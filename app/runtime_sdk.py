"""Claude Agent SDK runtime bridge.

Each browser live session owns exactly one ClaudeSDKClient instance
plus one async lock so only one active task runs per session at a time.

Requires the Claude Agent SDK for live sessions. Endpoint routing may be
configured via environment variables such as ANTHROPIC_BASE_URL for local
Anthropic-compatible providers like Ollama.

Package: pip install claude-agent-sdk
Docs:    https://code.claude.com/docs/en/agent-sdk/python

Mock mode:
  When claude-agent-sdk is not installed the app runs in mock mode.
  Sessions are created normally, prompts are echoed back token-by-token,
  and all UI streaming paths are exercised.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import get_provider_env, get_tool_search_env
from app.event_store import append_event
from app.hooks import HookContext, run_hooks
from app.mock_sdk import MockSDKClient, MockStreamEvent
from app.normalizer import (
    normalize_assistant_completed,
    normalize_session_failed,
    normalize_system_message,
    normalize_text_delta,
    normalize_tool_completed,
    normalize_tool_delta,
    normalize_tool_permission_decided,
    normalize_tool_started,
)
from app.schemas import PROTOCOL_VERSION, SessionCreateRequest, WSEnvelope
from app.websocket_manager import ws_manager

log = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """
You are PlexClaw, a repo-aware coding assistant running inside
the user's current working directory.

Core behavior:
- Be practical, concise, and action-oriented.
- Default to helping with code, debugging, shell commands,
  repo navigation, and implementation tasks.
- Prefer direct answers and concrete next steps over
  generic brainstorming.
- When the user is working in a repository, stay grounded in
  that repository and its files.

Response style:
- Use plain natural language.
- Do not emit fake XML or pseudo-tool markup such as
  <tool_call>, </tool_call>, <function_call>, or similar tags
  in normal responses.
- Do not narrate hidden chain-of-thought.
- Keep the first reply short unless the user asks for depth.
- When useful, give a minimal sequence of next steps instead
  of a long essay.

Tool behavior:
- Use tools only when needed.
- Do not claim to have run commands, inspected files, or
  changed code unless that actually happened.
- If a tool is unavailable or a file has not been inspected,
  say so briefly and continue with the best concrete guidance
  you can.
- When suggesting commands or patches, make them copy-pasteable.

Coding behavior:
- Prefer small, safe edits over sweeping rewrites.
- Preserve existing project conventions when they are visible.
- When uncertain, ask one focused clarifying question rather
  than making broad assumptions.

Grounding rules:
- When referencing filesystem paths, error messages, or configuration
  details, rely only on information explicitly present in the current
  conversation, inspected files, tool outputs, or runtime metadata.
- Do not invent placeholder paths such as /home/user or generic
  environment details that have not been observed in this session.
- If you have not inspected the relevant files or logs yet, say so
  briefly instead of implying that you have.
- When guidance is general rather than repo-specific, label it as
  general guidance instead of presenting it as a fact about this
  exact environment.

If the user starts with a direct engineering task, respond
like an experienced pair programmer already inside the project.
""".strip()


def build_effective_system_prompt(base_prompt: str, cwd: str | None) -> str:
    parts = [base_prompt.strip()]
    if cwd:
        parts.append(
            (
                "Runtime grounding:\n"
                f"- The active working directory for this session is: {cwd}\n"
                "- Treat this directory as the default repo/project root.\n"
                "- Do not invent other filesystem roots, home directories, or placeholder paths "
                "such as /home/user unless they are explicitly shown by the environment or the user.\n"
                "- Before giving filesystem-specific advice, prefer to inspect the actual repo/files "
                "or clearly state that you have not inspected them yet.\n"
                "- If you mention a path, prefer paths relative to the active working directory when possible."
            )
        )
    return "\n\n".join(part for part in parts if part.strip())


def _provider_env(provider: str) -> dict[str, str]:
    return get_provider_env(provider)


def _tool_search_env(mode: str | None) -> dict[str, str]:
    return get_tool_search_env(mode)


# ---------------------------------------------------------------------------
# SDK import — real package is `claude-agent-sdk` (pip install claude-agent-sdk)
# ---------------------------------------------------------------------------
try:
    import claude_agent_sdk as sdk  # type: ignore
    from claude_agent_sdk import (  # type: ignore
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
    )
    from claude_agent_sdk import (
        get_session_info as _sdk_get_session_info,
    )
    from claude_agent_sdk import (
        get_session_messages as _sdk_get_session_messages,
    )
    from claude_agent_sdk import (
        list_sessions as _sdk_list_sessions,
    )
    from claude_agent_sdk import (
        rename_session as _sdk_rename_session,
    )
    from claude_agent_sdk import (
        tag_session as _sdk_tag_session,
    )
    from claude_agent_sdk.types import StreamEvent  # type: ignore

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
        "claude_agent_sdk not installed — running in MOCK MODE. "
        "Install with: pip install claude-agent-sdk and configure "
        "ANTHROPIC_API_KEY for real Claude Code sessions."
    )


@dataclass
class LiveSession:
    id: str
    model: str
    cwd: str | None
    provider: str
    permission_mode: str
    resume_session_id: str | None
    fork_session: bool
    status: str = "created"  # created | ready | running | interrupted | failed
    last_activity_at: float = field(default_factory=time.monotonic)
    title: str = ""
    tag: str | None = None
    seq: int = 0
    _client: Any = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _approval_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _pending_tool_id: str | None = field(default=None, repr=False)
    _pending_tool_name: str | None = field(default=None, repr=False)
    _pending_tool_input: Any = field(default=None, repr=False)
    _approval_decision: str | None = field(default=None, repr=False)
    context_files: dict[str, str] = field(default_factory=dict, repr=False)
    _context_injected: bool = field(default=False, repr=False)
    mock_mode: bool = field(default=False, repr=False)

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


_sessions: dict[str, LiveSession] = {}


def get_session(session_id: str) -> LiveSession | None:
    return _sessions.get(session_id)


def list_live_sessions() -> list[LiveSession]:
    return list(_sessions.values())


def touch_session(session: LiveSession) -> None:
    session.last_activity_at = time.monotonic()


def get_idle_timeout_seconds() -> float:
    raw = os.getenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "1800").strip()
    try:
        value = float(raw)
    except ValueError:
        return 1800.0
    return max(60.0, value)


def get_reap_interval_seconds() -> float:
    raw = os.getenv("PLEXCLAW_SESSION_REAP_INTERVAL_SECONDS", "60").strip()
    try:
        value = float(raw)
    except ValueError:
        return 60.0
    return max(5.0, value)


async def reap_idle_sessions(now: float | None = None) -> list[str]:
    cutoff_now = time.monotonic() if now is None else now
    idle_timeout = get_idle_timeout_seconds()
    reaped: list[str] = []

    for session in list(_sessions.values()):
        conn_count = ws_manager.connection_count(session.id)

        if session.status == "deleted":
            log.info(
                "Reaping deleted live session session_id=%s status=%s connections=%s",
                session.id,
                session.status,
                conn_count,
            )
            reaped.append(session.id)
            await delete_session(session.id)
            continue

        idle_for = cutoff_now - session.last_activity_at
        if idle_for < idle_timeout:
            continue
        if conn_count > 0:
            continue
        if session.status == "running":
            continue

        log.info(
            (
                "Reaping idle live session session_id=%s idle_for=%.3f "
                "status=%s connections=%s timeout=%s"
            ),
            session.id,
            idle_for,
            session.status,
            conn_count,
            idle_timeout,
        )
        reaped.append(session.id)
        await delete_session(session.id)

    return reaped


async def _await_tool_approval(
    session: LiveSession,
    tool_id: str,
    tool_name: str,
    tool_input: Any,
) -> bool:
    session._pending_tool_id = tool_id
    session._pending_tool_name = tool_name
    session._pending_tool_input = tool_input
    session._approval_decision = None
    session._approval_event.clear()

    env = WSEnvelope(
        type="tool.permission_required",
        session_id=session.id,
        seq=session.next_seq(),
        payload={
            "tool_id": tool_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "status": "pending",
        },
        protocol_version=PROTOCOL_VERSION,
    )
    await _emit(session, env)
    await session._approval_event.wait()

    decision = session._approval_decision == "approve"
    session._pending_tool_id = None
    session._pending_tool_name = None
    session._pending_tool_input = None
    session._approval_decision = None
    return decision


async def approve_tool_call(session_id: str, tool_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if session._pending_tool_id != tool_id:
        raise KeyError(f"Tool {tool_id} is not pending for session {session_id}")
    session._approval_decision = "approve"
    env = normalize_tool_permission_decided(
        session.id,
        session.next_seq(),
        tool_id,
        session._pending_tool_name or "unknown",
        session._pending_tool_input,
        "approve",
    )
    await _emit(session, env)
    session._approval_event.set()


async def reject_tool_call(session_id: str, tool_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if session._pending_tool_id != tool_id:
        raise KeyError(f"Tool {tool_id} is not pending for session {session_id}")
    session._approval_decision = "reject"
    env = normalize_tool_permission_decided(
        session.id,
        session.next_seq(),
        tool_id,
        session._pending_tool_name or "unknown",
        session._pending_tool_input,
        "reject",
    )
    await _emit(session, env)
    session._approval_event.set()


def list_context_files(session_id: str) -> list[dict[str, str | int]]:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    return [
        {"filename": name, "size": len(content.encode("utf-8"))}
        for name, content in session.context_files.items()
    ]


def add_context_file(
    session_id: str, filename: str, content: str
) -> dict[str, str | int]:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if len(session.context_files) >= 10 and filename not in session.context_files:
        raise ValueError("maximum 10 context files allowed")
    size = len(content.encode("utf-8"))
    if size > 200 * 1024:
        raise ValueError("file exceeds 200KB limit")
    session.context_files[filename] = content
    session._context_injected = False
    return {"filename": filename, "size": size}


def remove_context_file(session_id: str, filename: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if filename not in session.context_files:
        raise KeyError(f"context file not found: {filename}")
    del session.context_files[filename]
    session._context_injected = False


def _inject_context_into_prompt(session: LiveSession, prompt: str) -> str:
    if not session.context_files:
        return prompt
    if session._context_injected:
        return prompt

    parts = ["Attached file context:"]
    for filename, content in session.context_files.items():
        parts.append(f"\n--- FILE: {filename} ---\n{content}")
    parts.append(f"\n--- USER PROMPT ---\n{prompt}")

    session._context_injected = True
    return "\n".join(parts)


async def _emit(session: LiveSession, envelope: WSEnvelope) -> None:
    """Broadcast, persist to event store, and run hooks."""
    touch_session(session)
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


async def update_session(
    session_id: str, *, permission_mode: str | None = None
) -> LiveSession:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")

    if permission_mode is not None:
        if permission_mode not in {"auto", "manual"}:
            raise ValueError(f"invalid permission_mode: {permission_mode}")
        session.permission_mode = permission_mode

    return session


async def create_session(req: SessionCreateRequest) -> LiveSession:
    normalized_cwd = None
    if req.cwd:
        normalized_cwd = str(Path(req.cwd).expanduser().resolve())
        p = Path(normalized_cwd)
        if not p.exists():
            raise ValueError(f"cwd does not exist: {p}")
        if not p.is_dir():
            raise ValueError(f"cwd is not a directory: {p}")

    session_id = str(uuid.uuid4())
    mock_mode = not _SDK_AVAILABLE

    session = LiveSession(
        id=session_id,
        model=req.model,
        cwd=normalized_cwd,
        provider=req.provider,
        permission_mode=req.permission_mode,
        resume_session_id=req.resume_session_id,
        fork_session=req.fork_session,
        mock_mode=mock_mode,
    )
    _sessions[session_id] = session
    touch_session(session)

    effective_system_prompt = build_effective_system_prompt(
        req.system_prompt or DEFAULT_SYSTEM_PROMPT,
        normalized_cwd,
    )
    provider_env = get_provider_env(req.provider)
    tool_search_env = get_tool_search_env(req.tool_search_mode)
    session_env = {**provider_env, **tool_search_env}
    provider_base_url = provider_env.get("ANTHROPIC_BASE_URL")

    if mock_mode:
        session._client = MockSDKClient(options=None)
    else:
        options = ClaudeAgentOptions(
            model=req.model,
            cwd=normalized_cwd,
            permission_mode=req.permission_mode,
            system_prompt=effective_system_prompt,
            resume=req.resume_session_id,
            fork_session=req.fork_session,
            include_partial_messages=True,
            env=session_env,
        )
        session._client = ClaudeSDKClient(options)

    log.info(
        "Session created: %s model=%s provider=%s cwd=%s mock=%s",
        session_id,
        req.model,
        req.provider,
        normalized_cwd,
        mock_mode,
    )

    session.seq += 1
    await _emit(
        session,
        WSEnvelope(
            protocol_version=PROTOCOL_VERSION,
            session_id=session.id,
            seq=session.seq,
            type="system.message",
            payload={
                "subtype": "session.created",
                "message": (
                    "Session created"
                    + (" [MOCK MODE — SDK not installed]" if mock_mode else ".")
                ),
                "model": session.model,
                "provider": session.provider,
                "provider_base_url": provider_base_url,
                "tool_search_mode": req.tool_search_mode,
                "tool_search_active": bool(req.tool_search_mode),
                "cwd": session.cwd,
                "permission_mode": session.permission_mode,
                "resume_session_id": session.resume_session_id,
                "fork_session": session.fork_session,
                "mock_mode": mock_mode,
            },
        ),
    )
    return session



def _iter_message_blocks(message: Any) -> Iterable[Any]:
    content = getattr(message, "content", None)
    if isinstance(content, list):
        return content
    return []


def _block_type(block: Any) -> str | None:
    if isinstance(block, dict):
        return block.get("type")
    return getattr(block, "type", None)


def _block_attr(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _coerce_tool_result_output(content: Any) -> Any:
    if isinstance(content, list) and len(content) == 1:
        item = content[0]
        if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
            return item.get("text")
    return content


async def _emit_tool_completed_from_message(
    session: LiveSession,
    message: Any,
    pending_tools: dict[str, dict[str, Any]],
) -> None:
    parent_tool_use_id = getattr(message, "parent_tool_use_id", None)

    for block in _iter_message_blocks(message):
        btype = _block_type(block)

        is_tool_result = btype == "tool_result" or (
            type(block).__name__ == "ToolResultBlock"
        )
        if not is_tool_result:
            continue

        tool_id = _block_attr(block, "tool_use_id")
        if not tool_id:
            tool_id = parent_tool_use_id
        if not tool_id:
            continue

        meta = pending_tools.pop(tool_id, {})
        tool_name = meta.get("tool_name", "tool")
        output = _coerce_tool_result_output(_block_attr(block, "content"))
        is_error = bool(_block_attr(block, "is_error", False))

        env = normalize_tool_completed(
            session.id,
            session.next_seq(),
            str(tool_id),
            str(tool_name),
            output,
            is_error=is_error,
        )
        await _emit(session, env)



def _is_mock_event(message: Any) -> bool:
    """Return True if message is a MockStreamEvent.

    Real StreamEvent checks handle the real SDK path.
    """
    return isinstance(message, MockStreamEvent)


async def _stream_sdk(session: LiveSession, prompt: str) -> None:
    """Real Claude Agent SDK streaming (also handles MockSDKClient transparently).

    Message flow with include_partial_messages=True:
        StreamEvent(message_start)
        StreamEvent(content_block_start)   — type="text" or type="tool_use"
        StreamEvent(content_block_delta)
            — delta.type="text_delta" | "input_json_delta"
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
    _pending_tools: dict[str, dict[str, Any]] = {}

    try:
        # ClaudeSDKClient (and MockSDKClient) must be connected before querying
        await client.connect()
        await client.query(prompt=prompt)

        async for message in client.receive_response():
            # ------------------------------------------------------------------
            # StreamEvent / MockStreamEvent: token-level incremental updates
            # ------------------------------------------------------------------
            is_stream = (
                _is_mock_event(message)
                or (StreamEvent is not None and isinstance(message, StreamEvent))
            )
            if is_stream:
                event: dict = message.event
                etype = event.get("type")

                if etype == "content_block_start":
                    cb = event.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        _current_tool_id = cb.get("id", str(uuid.uuid4()))
                        _current_tool_name = cb.get("name", "unknown")
                        _current_tool_json = ""
                        _pending_tools[_current_tool_id] = {
                            "tool_name": _current_tool_name,
                            "tool_input": {},
                        }
                        env = normalize_tool_started(
                            session.id,
                            session.next_seq(),
                            _current_tool_id,
                            _current_tool_name,
                            {},  # input streamed later via input_json_delta
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
                    if _current_tool_id and _current_tool_name:
                        import json as _json

                        try:
                            tool_input = (
                                _json.loads(_current_tool_json)
                                if _current_tool_json
                                else {}
                            )
                        except Exception:
                            tool_input = {"_raw": _current_tool_json}

                        if _current_tool_id in _pending_tools:
                            _pending_tools[_current_tool_id]["tool_input"] = tool_input

                        env = normalize_tool_delta(
                            session.id,
                            session.next_seq(),
                            _current_tool_id,
                            "",
                        )
                        env.payload["tool_input"] = tool_input
                        env.payload["tool_name"] = _current_tool_name
                        await _emit(session, env)

                        if session.permission_mode == "manual":
                            approved = await _await_tool_approval(
                                session,
                                _current_tool_id,
                                _current_tool_name,
                                tool_input,
                            )
                            if not approved:
                                reject_env = normalize_tool_completed(
                                    session.id,
                                    session.next_seq(),
                                    _current_tool_id,
                                    _current_tool_name,
                                    {"status": "rejected"},
                                    is_error=True,
                                )
                                _pending_tools.pop(_current_tool_id, None)
                                await _emit(session, reject_env)
                                if session._client:
                                    try:
                                        await session._client.interrupt()
                                    except Exception as exc:
                                        log.warning(
                                            "Interrupt after reject failed: %s", exc
                                        )

                        _current_tool_id = None
                        _current_tool_name = None
                        _current_tool_json = ""

                elif etype == "message_delta":
                    delta = event.get("delta", {})
                    usage = event.get("usage", {})
                    stop_reason = delta.get("stop_reason", "end_turn")
                    env = normalize_assistant_completed(
                        session.id, session.next_seq(), stop_reason, usage
                    )
                    await _emit(session, env)

                # message_start / message_stop / content_block_stop (text) are no-ops
                continue

            # ------------------------------------------------------------------
            # AssistantMessage: complete assembled message (no-op — already streamed)
            # ------------------------------------------------------------------
            if AssistantMessage is not None and isinstance(message, AssistantMessage):
                await _emit_tool_completed_from_message(
                    session, message, _pending_tools
                )
                continue

            # ------------------------------------------------------------------
            # ResultMessage: final result — signals end of turn
            # ------------------------------------------------------------------
            if ResultMessage is not None and isinstance(message, ResultMessage):
                stop_reason = getattr(message, "subtype", "end_turn")
                usage = {}
                raw_usage = getattr(message, "usage", None)
                if raw_usage is not None:
                    usage = (
                        vars(raw_usage)
                        if hasattr(raw_usage, "__dict__")
                        else dict(raw_usage)
                    )
                env = normalize_assistant_completed(
                    session.id, session.next_seq(), stop_reason, usage
                )
                await _emit(session, env)

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

    touch_session(session)

    async with session._lock:
        if session._client is None:
            raise RuntimeError("Session client is not initialized")

        session.status = "running"
        sys_env = normalize_system_message(
            session.id,
            session.next_seq(),
            f"Prompt received ({len(prompt)} chars)",
        )
        await _emit(session, sys_env)

        try:
            prompt_with_context = _inject_context_into_prompt(session, prompt)
            await _stream_sdk(session, prompt_with_context)
        finally:
            if session.status != "failed":
                session.status = "ready"


async def interrupt_session(session_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if session._client:
        try:
            await session._client.interrupt()
            if not session.mock_mode:
                # Only drain the real SDK response queue
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


async def delete_session(session_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")

    if session._client:
        try:
            interrupt = getattr(session._client, "interrupt", None)
            if interrupt is not None:
                await interrupt()
        except Exception as exc:
            log.warning("Session delete interrupt failed: %s", exc)

        try:
            close = getattr(session._client, "close", None)
            if close is not None:
                result = close()
                if hasattr(result, "__await__"):
                    await result
        except Exception as exc:
            log.warning("Session delete close failed: %s", exc)

    session.context_files.clear()
    session._pending_tool_id = None
    session._pending_tool_name = None
    session._pending_tool_input = None
    session._approval_decision = None
    session._context_injected = False
    session.status = "deleted"
    session._client = None

    _sessions.pop(session_id, None)


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


def _archive_messages_to_events(session_id: str, messages: list[dict]) -> list[dict]:
    events: list[dict] = []
    seq = 1

    def push(env) -> None:
        nonlocal seq
        if hasattr(env, "model_dump"):
            events.append(env.model_dump())
        else:
            events.append(dict(env))
        seq += 1

    for item in messages:
        msg = item.get("message") or {}
        role = msg.get("role")
        content = msg.get("content")

        if role == "assistant":
            saw_text = False

            if isinstance(content, str):
                if content:
                    push(normalize_text_delta(session_id, seq, content))
                    saw_text = True

            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    btype = block.get("type")

                    if btype == "text":
                        text = block.get("text", "")
                        if text:
                            push(normalize_text_delta(session_id, seq, text))
                            saw_text = True

                    elif btype == "tool_use":
                        tool_id = str(block.get("id", ""))
                        tool_name = str(block.get("name", "tool"))
                        tool_input = block.get("input", {}) or {}

                        push(
                            normalize_tool_started(
                                session_id,
                                seq,
                                tool_id,
                                tool_name,
                                {},
                            )
                        )

                        env = normalize_tool_delta(
                            session_id,
                            seq,
                            tool_id,
                            "",
                        )
                        env.payload["tool_name"] = tool_name
                        env.payload["tool_input"] = tool_input
                        push(env)

                    else:
                        push(
                            normalize_system_message(
                                session_id,
                                seq,
                                f"Unsupported archive assistant block: {btype}",
                                level="warn",
                            )
                        )

            if saw_text or content:
                push(
                    normalize_assistant_completed(
                        session_id,
                        seq,
                        msg.get("stop_reason", "end_turn"),
                    )
                )

        elif role == "user":
            continue

        else:
            push(
                normalize_system_message(
                    session_id,
                    seq,
                    f"Unsupported archive message role: {role or item.get('type')}",
                    level="warn",
                )
            )

    return events


async def list_archive_sessions() -> list[dict]:
    if not _SDK_AVAILABLE:
        return []
    loop = asyncio.get_running_loop()
    try:
        raw: list = await loop.run_in_executor(None, _sdk_list_sessions)
        sessions = [_sdksession_to_dict(s) for s in (raw or [])]
        sessions.sort(key=lambda s: s.get("last_modified") or 0, reverse=True)
        return sessions
    except Exception as exc:
        log.warning("list_sessions error: %s", exc)
        return []


async def get_archive_session(session_id: str) -> dict:
    if not _SDK_AVAILABLE:
        return {"id": session_id}
    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, _sdk_get_session_info, session_id)
        return _sdksession_to_dict(info) or {"id": session_id}
    except Exception as exc:
        log.warning("get_session_info error: %s", exc)
        return {"id": session_id}


async def get_archive_messages(session_id: str) -> list:
    if not _SDK_AVAILABLE:
        return []
    loop = asyncio.get_running_loop()
    try:
        raw: list = await loop.run_in_executor(
            None, _sdk_get_session_messages, session_id
        )
        return [_sdkmessage_to_dict(m) for m in (raw or [])]
    except Exception as exc:
        log.warning("get_session_messages error: %s", exc)
        return []


async def get_archive_replay_events(session_id: str) -> list[dict]:
    messages = await get_archive_messages(session_id)
    return _archive_messages_to_events(session_id, messages)


async def rename_archive_session(session_id: str, title: str) -> None:
    if not _SDK_AVAILABLE:
        return
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _sdk_rename_session, session_id, title)
    except Exception as exc:
        log.warning("rename_session error: %s", exc)


async def tag_archive_session(session_id: str, tag: str | None) -> None:
    if not _SDK_AVAILABLE:
        return
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _sdk_tag_session, session_id, tag)
    except Exception as exc:
        log.warning("tag_session error: %s", exc)
