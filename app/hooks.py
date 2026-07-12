"""Hook system for audit, approval, and policy extensions.

Initially lightweight – logs events and emits system.message payloads.
Future work can replace these stubs with real policy/approval logic
without re-architecting the runtime.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)


class HookContext:
    """Carries context delivered to every hook."""

    def __init__(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        self.session_id = session_id
        self.event_type = event_type
        self.payload = payload


HookFn = Callable[[HookContext], Awaitable[None]]

_hooks: list[HookFn] = []


def register_hook(fn: HookFn) -> None:
    """Register an async hook function."""
    _hooks.append(fn)


async def run_hooks(ctx: HookContext) -> None:
    """Fire all registered hooks; errors are logged, not raised."""
    for fn in _hooks:
        try:
            await fn(ctx)
        except Exception as exc:  # noqa: BLE001
            log.error("Hook %s raised: %s", fn.__name__, exc)


# Default logging hook
async def _log_hook(ctx: HookContext) -> None:
    log.debug(
        "[hook] session=%s type=%s",
        ctx.session_id,
        ctx.event_type,
    )


register_hook(_log_hook)


def unregister_hook(fn) -> None:
    """Remove a previously registered hook if present."""
    try:
        _hooks.remove(fn)
    except ValueError:
        pass


def reset_hooks() -> None:
    """Reset hook registry to the default built-in hooks."""
    global _hooks
    _hooks[:] = [_log_hook]


def describe_hook_event(event_type: str, payload: dict[str, Any]) -> str:
    tool_name = payload.get("tool_name") or payload.get("tool") or "tool"
    decision = payload.get("decision") or "unknown"
    stop_reason = payload.get("stop_reason") or payload.get("reason") or "unknown"
    level = payload.get("level") or "info"
    text = payload.get("text") or payload.get("message")

    if event_type == "session.start":
        return "Hook observed session start."
    if event_type == "session.end":
        return "Hook observed session end."
    if event_type == "session.interrupted":
        return f"Stop observed ({stop_reason})."
    if event_type == "assistant.completed":
        return f"Assistant completed with stop reason: {stop_reason}."
    if event_type == "pre_tool":
        return f"Hook observed pre-tool event for {tool_name}."
    if event_type == "post_tool":
        return f"Hook observed post-tool event for {tool_name}."
    if event_type == "tool.permission_required":
        return f"PermissionRequest observed for {tool_name}."
    if event_type == "tool.permission_decided":
        return f"PermissionDecision observed for {tool_name}: {decision}."
    if event_type == "tool.completed":
        return f"Tool completed: {tool_name}."
    if event_type == "system.message":
        if text:
            return f"Notification ({level}): {text}"
        return f"Notification observed ({level})."
    if event_type == "session.failed":
        return "Session failure observed."

    return f"Hook observed {event_type}."

def hook_system_message(ctx: HookContext) -> dict[str, Any]:
    return {
        "kind": "hook.event",
        "event_type": ctx.event_type,
        "message": describe_hook_event(ctx.event_type, ctx.payload),
        "payload": ctx.payload,
    }
