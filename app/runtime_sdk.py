"""Claude Agent SDK runtime bridge.

Each browser live session owns exactly one ClaudeSDKClient instance
plus one async lock so only one active task runs per session at a time.

Requires the Claude Agent SDK for live sessions. Endpoint routing may be
configured via environment variables such as ANTHROPIC_BASE_URL for local
Anthropic-compatible providers like Ollama.

Package: pip install claude-agent-sdk
Docs:    https://code.claude.com/docs/en/agent-sdk/python
"""
from __future__ import annotations

DEFAULT_SYSTEM_PROMPT = """
You are PlexClaw, a repo-aware coding assistant running inside the user's current working directory.

Core behavior:
- Be practical, concise, and action-oriented.
- Default to helping with code, debugging, shell commands, repo navigation, and implementation tasks.
- Prefer direct answers and concrete next steps over generic brainstorming.
- When the user is working in a repository, stay grounded in that repository and its files.

Response style:
- Use plain natural language.
- Do not emit fake XML or pseudo-tool markup such as <tool_call>, </tool_call>, <function_call>, or similar tags in normal responses.
- Do not narrate hidden chain-of-thought.
- Keep the first reply short unless the user asks for depth.
- When useful, give a minimal sequence of next steps instead of a long essay.

Tool behavior:
- Use tools only when needed.
- Do not claim to have run commands, inspected files, or changed code unless that actually happened.
- If a tool is unavailable or a file has not been inspected, say so briefly and continue with the best concrete guidance you can.
- When suggesting commands or patches, make them copy-pasteable.

Coding behavior:
- Prefer small, safe edits over sweeping rewrites.
- Preserve existing project conventions when they are visible.
- When uncertain, ask one focused clarifying question rather than making broad assumptions.

If the user starts with a direct engineering task, respond like an experienced pair programmer already inside the project.
""".strip()

import asyncio
import logging
import uuid
from pathlib import Path
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
        "claude_agent_sdk not installed. "
        "Install with: pip install claude-agent-sdk and configure local routing with ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN as needed."
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
    _approval_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _pending_tool_id: Optional[str] = field(default=None, repr=False)
    _pending_tool_name: Optional[str] = field(default=None, repr=False)
    _pending_tool_input: Any = field(default=None, repr=False)
    _approval_decision: Optional[str] = field(default=None, repr=False)
    context_files: dict[str, str] = field(default_factory=dict, repr=False)
    _context_injected: bool = field(default=False, repr=False)

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


_sessions: dict[str, LiveSession] = {}


def get_session(session_id: str) -> Optional[LiveSession]:
    return _sessions.get(session_id)


def list_live_sessions() -> list[LiveSession]:
    return list(_sessions.values())


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
    session._approval_event.set()


async def reject_tool_call(session_id: str, tool_id: str) -> None:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    if session._pending_tool_id != tool_id:
        raise KeyError(f"Tool {tool_id} is not pending for session {session_id}")
    session._approval_decision = "reject"
    session._approval_event.set()


def list_context_files(session_id: str) -> list[dict[str, str | int]]:
    session = _sessions.get(session_id)
    if not session:
        raise KeyError(f"Session {session_id} not found")
    return [
        {"filename": name, "size": len(content.encode("utf-8"))}
        for name, content in session.context_files.items()
    ]


def add_context_file(session_id: str, filename: str, content: str) -> dict[str, str | int]:
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



async def update_session(session_id: str, *, permission_mode: Optional[str] = None) -> LiveSession:
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

  if not _SDK_AVAILABLE:
      raise RuntimeError(
          "claude_agent_sdk is not installed. Install it with "
          "'pip install claude-agent-sdk' and configure "
          "ANTHROPIC_BASE_URL=http://localhost:11434 plus "
          "ANTHROPIC_AUTH_TOKEN=ollama for local Ollama use."
      )

  session_id = str(uuid.uuid4())
  session = LiveSession(
      id=session_id,
      model=req.model,
      cwd=normalized_cwd,
      provider=req.provider,
      permission_mode=req.permission_mode,
      resume_session_id=req.resume_session_id,
      fork_session=req.fork_session,
  )
  _sessions[session_id] = session

  # Conservative default system prompt to reduce over-aggressive tool use.
  # If the frontend supplied a system_prompt, respect it; otherwise, use this.
  default_system_prompt = (
      "You are a coding assistant inside PlexClaw.\n"
      "\n"
      "Respond in plain natural language unless a real tool call is necessary. "
      "Do not emit XML, pseudo-XML, tool tags, function-call markup, or schema markup as assistant text.\n"
      "\n"
      "Prefer answering directly in plain language when the user asks for "
      "explanation, planning, review, summary, or small code snippets that do not "
      "require modifying files or inspecting the filesystem.\n"
      "\n"
      "Use tools only when they are genuinely necessary to complete the "
      "request accurately, such as reading project files, searching the "
      "codebase, or writing requested changes.\n"
      "\n"
      "Before using a write or edit tool, briefly explain what you plan to "
      "change unless the user explicitly asked for immediate file modification.\n"
      "\n"
      "Do not create files, reports, workflows, or analysis documents unless "
      "the user explicitly asks for them.\n"
      "\n"
      "If you are not actually calling a tool through the runtime, never simulate "
      "a tool call in text and never print tags like <tool_call>, <function>, "
      "<parameter>, or similar markup.\n"
      "\n"
      "When a concise direct answer is sufficient, respond without calling tools."
  )
  effective_system_prompt = req.system_prompt or default_system_prompt

  options = ClaudeAgentOptions(
      model=req.model,
      cwd=normalized_cwd,
      permission_mode=req.permission_mode,
      system_prompt=effective_system_prompt,
      resume=req.resume_session_id,
      fork_session=req.fork_session,
      include_partial_messages=True,
  )
  session._client = ClaudeSDKClient(options)

  log.info("Session created: %s model=%s provider=%s cwd=%s", session_id, req.model, req.provider, normalized_cwd)

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
              "message": "Session created.",
              "model": session.model,
              "provider": session.provider,
              "cwd": session.cwd,
              "permission_mode": session.permission_mode,
              "resume_session_id": session.resume_session_id,
              "fork_session": session.fork_session,
          },
      ),
  )
  return session

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
                                await _emit(session, reject_env)
                                if _SDK_AVAILABLE and session._client:
                                    try:
                                        await session._client.interrupt()
                                    except Exception as exc:
                                        log.warning("Interrupt after reject failed: %s", exc)

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
       if not _SDK_AVAILABLE:
           raise RuntimeError(
               "claude_agent_sdk is not installed. Install it with "
               "'pip install claude-agent-sdk' and configure "
               "ANTHROPIC_BASE_URL=http://localhost:11434 plus "
               "ANTHROPIC_AUTH_TOKEN=ollama for local Ollama use."
           )
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
        sessions = [_sdksession_to_dict(s) for s in (raw or [])]
        sessions.sort(key=lambda s: (s.get("last_modified") or 0), reverse=True)
        return sessions
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