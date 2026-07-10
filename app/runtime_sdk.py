"""Claude Agent SDK runtime bridge.

Each browser live session owns exactly one ClaudeSDKClient instance
plus one async lock so only one active task runs per session at a time.

Falls back to a mock streaming mode when the claude_code_sdk package is
not installed so the UI can be developed / demoed without real API keys.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from app.event_store import append_event
from app.hooks import HookContext, run_hooks
from app.normalizer import (
    normalize_assistant_completed,
    normalize_session_failed,
    normalize_system_message,
    normalize_text_delta,
    normalize_tool_completed,
    normalize_tool_delta,
    normalize_tool_started,
)
from app.schemas import PROTOCOL_VERSION, SessionCreateRequest, WSEnvelope
from app.websocket_manager import ws_manager

log = logging.getLogger(__name__)

try:
    import claude_code_sdk as sdk  # type: ignore

    _SDK_AVAILABLE = True
except ImportError:
    sdk = None  # type: ignore
    _SDK_AVAILABLE = False
    log.warning(
        "claude_code_sdk not installed – running in MOCK mode. "
        "Install the package and set ANTHROPIC_API_KEY for live use."
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
        options = sdk.ClaudeAgentOptions(
            model=req.model,
            cwd=req.cwd,
            permission_mode=req.permission_mode,
            system_prompt=req.system_prompt,
        )
        if req.resume_session_id:
            options.resume_session_id = req.resume_session_id
            options.fork_session = req.fork_session
        session._client = sdk.ClaudeSDKClient(options)

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
    """Real Claude SDK streaming."""
    client: Any = session._client
    try:
        async for event in client.query(prompt=prompt):
            etype = getattr(event, "type", None)

            if etype == "text" or hasattr(event, "text"):
                text = getattr(event, "text", "")
                if text:
                    env = normalize_text_delta(
                        session.id, session.next_seq(), text
                    )
                    await _emit(session, env)

            elif etype == "tool_use" or hasattr(event, "tool_use_id"):
                tool_id = getattr(event, "tool_use_id", str(uuid.uuid4()))
                tool_name = getattr(event, "name", "unknown")
                tool_input = getattr(event, "input", {})
                env = normalize_tool_started(
                    session.id, session.next_seq(), tool_id, tool_name, tool_input
                )
                await _emit(session, env)

            elif etype == "tool_result" or hasattr(event, "tool_use_id") and hasattr(event, "content"):
                tool_id = getattr(event, "tool_use_id", "")
                tool_name = getattr(event, "name", "tool")
                output = getattr(event, "content", "")
                is_error = getattr(event, "is_error", False)
                env = normalize_tool_completed(
                    session.id, session.next_seq(), tool_id, tool_name, output, is_error
                )
                await _emit(session, env)

            elif etype == "message_stop" or etype == "end_turn":
                stop_reason = getattr(event, "stop_reason", "end_turn")
                usage = getattr(event, "usage", {})
                if hasattr(usage, "__dict__"):
                    usage = vars(usage)
                env = normalize_assistant_completed(
                    session.id, session.next_seq(), stop_reason, usage
                )
                await _emit(session, env)
                break

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
        # Emit system message to confirm receipt
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
            session._client.interrupt()
            # Drain pending responses per SDK requirement
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
# Archive passthroughs (delegates to SDK or returns empty stubs)
# ---------------------------------------------------------------------------

async def list_archive_sessions() -> list[dict]:
    if _SDK_AVAILABLE:
        try:
            raw = await sdk.list_sessions()
            return raw if isinstance(raw, list) else []
        except Exception as exc:
            log.warning("list_sessions error: %s", exc)
    return []


async def get_archive_session(session_id: str) -> dict:
    if _SDK_AVAILABLE:
        try:
            return await sdk.get_session_info(session_id) or {}
        except Exception as exc:
            log.warning("get_session_info error: %s", exc)
    return {"id": session_id}


async def get_archive_messages(session_id: str) -> list:
    if _SDK_AVAILABLE:
        try:
            return await sdk.get_session_messages(session_id) or []
        except Exception as exc:
            log.warning("get_session_messages error: %s", exc)
    return []


async def rename_archive_session(session_id: str, title: str) -> None:
    if _SDK_AVAILABLE:
        try:
            await sdk.rename_session(session_id, title)
        except Exception as exc:
            log.warning("rename_session error: %s", exc)


async def tag_archive_session(session_id: str, tag: str | None) -> None:
    if _SDK_AVAILABLE:
        try:
            await sdk.tag_session(session_id, tag)
        except Exception as exc:
            log.warning("tag_session error: %s", exc)
