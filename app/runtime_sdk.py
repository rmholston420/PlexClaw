"""Claude Agent SDK runtime bridge.

Each browser live session owns exactly one ClaudeSDKClient instance
plus one async lock so only one active task runs per session at a time.

Falls back to a mock streaming mode when the claude_agent_sdk package is
not installed so the UI can be developed / demoed without real API keys.

Package: pip install claude-agent-sdk
Docs:    https://code.claude.com/docs/en/agent-sdk/python
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.event_store import append_event
from app.hooks import HookContext, run_hooks
from app.normalizer import (
    normalize_assistant_completed,
    normalize_session_failed,
    normalize_system_message,
    normalize_text_delta,
    normalize_tool_completed,
    normalize_tool_started,
)
from app.schemas import PROTOCOL_VERSION, SessionCreateRequest, WSEnvelope
from app.websocket_manager import ws_manager

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SDK import — real package is `claude-agent-sdk` (pip install claude-agent-sdk)
# ---------------------------------------------------------------------------
try:
    import claude_agent_sdk as sdk  # type: ignore
    from claude_agent_sdk.types import StreamEvent  # type: ignore
    from claude_agent_sdk import (  # type: ignore
        AssistantMessage,
        ResultMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        list_sessions as _sdk_list_sessions,
        get_session_info as _sdk_get_session_info,
        get_session_messages as _sdk_get_session_messages,
        rename_session as _sdk_rename_session,
        tag_session as _sdk_tag_session,
    )
    _SDK_AVAILABLE = True
except ImportError:
    sdk = None  # type: ignore
    StreamEvent = None  # type: ignore
    AssistantMessage = None  # type: ignore
    ResultMessage = None  # type: ignore
    ClaudeAgentOptions = None  # type: ignore
    ClaudeSDKClient = None  # type: ignore
    _sdk_list_sessions = None  # type: ignore
    _sdk_get_session_info = None  # type: ignore
    _sdk_get_session_messages = None  # type: ignore
    _sdk_rename_session = None  # type: ignore
    _sdk_tag_session = None  # type: ignore
    _SDK_AVAILABLE = False
    log.warning(
        "claude_agent_sdk not installed – running in MOCK mode. "
        "Install with: pip install claude-agent-sdk  and set ANTHROPIC_API_KEY."
    )


@dataclass
class LiveSession:
    id: str
    model: str
    cwd: Optional[str]
    provider: str
    permission_mode: str
    resume_session_id: Optional[str]
    fork_session: bool
    status: str = "created"  # created | ready | running | interrupted | failed
    title: str = ""
    tag: Optional[str] = None
    seq: int = 0
    _client: Any = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


_sessions: dict[str, LiveSession] = {}


def get_session(session_id: str) -> Optional[LiveSession]:
    return _sessions.get(session_id)


def list_live_sessions() -> list[LiveSession]:
    return list(_sessions.values())


async def _emit(session: LiveSession, envelope: WSEnvelope) -> None:
    """Broadcast, persist to event store, and run hooks."""
    await ws_manager.broadcast(envelope)
    append_event(
        session.id,
        envelope.seq,
        envelope.type,
        envelope.payload,
    )
    await run_hooks(
        HookContext(
            session_id=session.id,
            event_type=envelope.type,
            payload=envelope.payload,
        )
    )


async def create_session(req: SessionCreateRequest) -> LiveSession:
    session_id = str(uuid.uuid4())
    session = LiveSession(
        id=session_id,
        model=req.model,
        cwd=req.cwd,
        provider=req.provider,
        permission_mode=req.permission_mode,
        resume_session_id=req.resume_session_id,
        fork_session=req.fork_session,
    )
    _sessions[session_id] = session

    if _SDK_AVAILABLE:
        # ClaudeAgentOptions field names confirmed from Anthropic Python SDK docs:
        #   - system_prompt: valid constructor arg (str | SystemPromptPreset | None)
        #   - permission_mode: valid constructor arg (PermissionMode | None)
        #   - resume: str | None  — NOT resume_session_id
        #   - fork_session: bool  — valid constructor arg
        #   - include_partial_messages: bool — enables StreamEvent token-level streaming
        options = ClaudeAgentOptions(
            model=req.model,
            cwd=req.cwd,
            permission_mode=req.permission_mode,
            system_prompt=req.system_prompt,
            resume=req.resume_session_id,       # correct field name is `resume`
            fork_session=req.fork_session,
            include_partial_messages=True,      # required for token-level streaming
        )
        session._client = ClaudeSDKClient(options)

    log.info("Session created: %s (sdk=%s)", session_id, _SDK_AVAILABLE)
    return session


async def _stream_mock(session: LiveSession, prompt: str) -> None:
    """Fake streaming for dev/demo without real SDK."""
    words = f"[MOCK] Echo: {prompt}".split()
    for word in words:
        await asyncio.sleep(0.05)
        env = normalize_text_delta(session.id, session.next_seq(), word + " ")
        await _emit(session, env)
    completed = normalize_assistant_completed(
        session.id, session.next_seq(), "end_turn"
    )
    await _emit(session, completed)


async def _stream_sdk(session: LiveSession, prompt: str) -> None:
    """Real Claude Agent SDK streaming.

    Message flow with include_partial_messages=True:
        StreamEvent(message_start)
        StreamEvent(content_block_start)   — type="text" or type="tool_use"
        StreamEvent(content_block_delta)   — delta.type="text_delta" | "input_json_delta"
        StreamEvent(content_block_stop)
        StreamEvent(message_delta)         — stop_reason, usage
        StreamEvent(message_stop)
        AssistantMessage                   — complete assembled message
        ResultMessage                      — final result (end of turn)

    We drive UI updates from StreamEvents so the user sees tokens in real time,
    and confirm completion on ResultMessage.
    """
    client: Any = session._client
    # Accumulation state for the current tool_use block
    _current_tool_id: str | None = None
    _current_tool_name: str | None = None
    _current_tool_json: str = ""

    try:
        # ClaudeSDKClient must be connected before querying
        await client.connect()
        await client.query(prompt=prompt)

        async for message in client.receive_response():

            # ------------------------------------------------------------------
            # StreamEvent: token-level incremental updates
            # ------------------------------------------------------------------
            if StreamEvent is not None and isinstance(message, StreamEvent):
                event: dict = message.event
                etype = event.get("type")

                if etype == "content_block_start":
                    cb = event.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        _current_tool_id = cb.get("id", str(uuid.uuid4()))
                        _current_tool_name = cb.get("name", "unknown")
                        _current_tool_json = ""
                        env = normalize_tool_started(
                            session.id,
                            session.next_seq(),
                            _current_tool_id,
                            _current_tool_name,
                            {},  # input not yet available; streamed via input_json_delta
                        )
                        await _emit(session, env)

                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    dtype = delta.get("type")

                    if dtype == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            env = normalize_text_delta(
                                session.id, session.next_seq(), text
                            )
                            await _emit(session, env)

                    elif dtype == "input_json_delta" and _current_tool_id:
                        _current_tool_json += delta.get("partial_json", "")

                elif etype == "content_block_stop":
                    # Tool input fully assembled — emit completed tool_started with full input
                    if _current_tool_id and _current_tool_name:
                        import json as _json
                        try:
                            tool_input = _json.loads(_current_tool_json) if _current_tool_json else {}
                        except Exception:
                            tool_input = {"_raw": _current_tool_json}
                        # Re-emit with complete input by sending a delta payload
                        env = normalize_tool_started(
                            session.id,
                            session.next_seq(),
                            _current_tool_id,
                            _current_tool_name,
                            tool_input,
                        )
                        await _emit(session, env)
                        _current_tool_id = None
                        _current_tool_name = None
                        _current_tool_json = ""

                elif etype == "message_delta":
                    # stop_reason and usage arrive here
                    delta = event.get("delta", {})
                    usage = event.get("usage", {})
                    stop_reason = delta.get("stop_reason", "end_turn")
                    env = normalize_assistant_completed(
                        session.id, session.next_seq(), stop_reason, usage
                    )
                    await _emit(session, env)

            # ------------------------------------------------------------------
            # AssistantMessage: complete assembled message (no-op — already streamed)
            # ------------------------------------------------------------------
            elif AssistantMessage is not None and isinstance(message, AssistantMessage):
                pass  # content already emitted token-by-token via StreamEvents

            # ------------------------------------------------------------------
            # ResultMessage: final result — signals end of turn
            # ------------------------------------------------------------------
            elif ResultMessage is not None and isinstance(message, ResultMessage):
                stop_reason = getattr(message, "subtype", "end_turn")
                usage = {}
                raw_usage = getattr(message, "usage", None)
                if raw_usage is not None:
                    usage = vars(raw_usage) if hasattr(raw_usage, "__dict__") else dict(raw_usage)
                env = normalize_assistant_completed(
                    session.id, session.next_seq(), stop_reason, usage
                )
                await _emit(session, env)
                # ResultMessage is the final message in receive_response(); iteration ends here.

    except Exception as exc:
        log.error("SDK stream error session=%s: %s", session.id, exc)
        env = normalize_session_failed(session.id, session.next_seq(), str(exc))
        await _emit(session, env)
        session.status = "failed"
        raise


async def submit_prompt(session_id: str, prompt: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")

    async with session._lock:
        session.status = "running"
        sys_env = normalize_system_message(
            session.id,
            session.next_seq(),
            f"Prompt received ({len(prompt)} chars)",
        )
        await _emit(session, sys_env)

        try:
            if _SDK_AVAILABLE and session._client is not None:
                await _stream_sdk(session, prompt)
            else:
                await _stream_mock(session, prompt)
        finally:
            session.status = "ready"


async def interrupt_session(session_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if _SDK_AVAILABLE and session._client:
        try:
            # interrupt() is async per SDK docs
            await session._client.interrupt()
            # Drain the interrupted task's messages (including its ResultMessage)
            # before the client can accept a new query.
            async for _ in session._client.receive_response():
                pass
        except Exception as exc:
            log.warning("Interrupt drain error: %s", exc)
    session.status = "interrupted"
    env = WSEnvelope(
        type="session.interrupted",
        session_id=session_id,
        seq=session.next_seq(),
        payload={"reason": "user_interrupt"},
        protocol_version=PROTOCOL_VERSION,
    )
    await _emit(session, env)


# ---------------------------------------------------------------------------
# Archive passthroughs
#
# All five archive functions are SYNCHRONOUS top-level exports from
# claude_agent_sdk — NOT async, NOT methods on a client object.
# They read from local session storage files and return immediately.
# Run them in an executor thread to avoid blocking the event loop.
# ---------------------------------------------------------------------------

def _sdksession_to_dict(info: Any) -> dict:
    """Convert SDKSessionInfo dataclass to a JSON-serialisable dict."""
    if info is None:
        return {}
    return {
        "session_id": getattr(info, "session_id", ""),
        "summary": getattr(info, "summary", ""),
        "last_modified": getattr(info, "last_modified", 0),
        "file_size": getattr(info, "file_size", None),
        "custom_title": getattr(info, "custom_title", None),
        "first_prompt": getattr(info, "first_prompt", None),
        "git_branch": getattr(info, "git_branch", None),
        "cwd": getattr(info, "cwd", None),
        "tag": getattr(info, "tag", None),
        "created_at": getattr(info, "created_at", None),
    }


def _sdkmessage_to_dict(msg: Any) -> dict:
    """Convert SessionMessage dataclass to a JSON-serialisable dict."""
    if msg is None:
        return {}
    return {
        "type": getattr(msg, "type", ""),
        "uuid": getattr(msg, "uuid", ""),
        "session_id": getattr(msg, "session_id", ""),
        "message": getattr(msg, "message", None),
        "parent_tool_use_id": getattr(msg, "parent_tool_use_id", None),
    }


async def list_archive_sessions() -> list[dict]:
    if not _SDK_AVAILABLE:
        return []
    loop = asyncio.get_event_loop()
    try:
        raw: list = await loop.run_in_executor(None, _sdk_list_sessions)
        return [_sdksession_to_dict(s) for s in (raw or [])]
    except Exception as exc:
        log.warning("list_sessions error: %s", exc)
        return []


async def get_archive_session(session_id: str) -> dict:
    if not _SDK_AVAILABLE:
        return {"id": session_id}
    loop = asyncio.get_event_loop()
    try:
        info = await loop.run_in_executor(None, _sdk_get_session_info, session_id)
        return _sdksession_to_dict(info) or {"id": session_id}
    except Exception as exc:
        log.warning("get_session_info error: %s", exc)
        return {"id": session_id}


async def get_archive_messages(session_id: str) -> list:
    if not _SDK_AVAILABLE:
        return []
    loop = asyncio.get_event_loop()
    try:
        raw: list = await loop.run_in_executor(
            None, _sdk_get_session_messages, session_id
        )
        return [_sdkmessage_to_dict(m) for m in (raw or [])]
    except Exception as exc:
        log.warning("get_session_messages error: %s", exc)
        return []


async def rename_archive_session(session_id: str, title: str) -> None:
    if not _SDK_AVAILABLE:
        return
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _sdk_rename_session, session_id, title)
    except Exception as exc:
        log.warning("rename_session error: %s", exc)


async def tag_archive_session(session_id: str, tag: str | None) -> None:
    if not _SDK_AVAILABLE:
        return
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _sdk_tag_session, session_id, tag)
    except Exception as exc:
        log.warning("tag_session error: %s", exc)
