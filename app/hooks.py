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
