"""Unit tests for app/hooks.py.

Covers:
  - register_hook / run_hooks fan-out
  - hook errors are suppressed (logged, not raised)
  - unregister_hook removes the correct hook
  - unregister_hook on unknown fn is a no-op
  - reset_hooks restores exactly the default _log_hook
  - HookContext attributes are stored correctly
  - Multiple hooks run in registration order
"""
from __future__ import annotations

import pytest

from app.hooks import (
    HookContext,
    _hooks,
    register_hook,
    reset_hooks,
    run_hooks,
    unregister_hook,
)

# conftest already calls reset_hooks() after each test via the autouse fixture


# ---------------------------------------------------------------------------
# HookContext
# ---------------------------------------------------------------------------


def test_hook_context_stores_attributes():
    ctx = HookContext("sess1", "assistant.delta", {"text": "hi"})
    assert ctx.session_id == "sess1"
    assert ctx.event_type == "assistant.delta"
    assert ctx.payload == {"text": "hi"}


# ---------------------------------------------------------------------------
# register_hook / run_hooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registered_hook_is_called():
    calls: list[HookContext] = []

    async def my_hook(ctx: HookContext) -> None:
        calls.append(ctx)

    register_hook(my_hook)
    ctx = HookContext("s", "system.message", {})
    await run_hooks(ctx)

    assert len(calls) == 1
    assert calls[0] is ctx


@pytest.mark.asyncio
async def test_multiple_hooks_run_in_order():
    order: list[str] = []

    async def hook_a(ctx):
        order.append("a")

    async def hook_b(ctx):
        order.append("b")

    register_hook(hook_a)
    register_hook(hook_b)
    await run_hooks(HookContext("s", "t", {}))

    # default _log_hook fires first, then a then b
    assert order[-2:] == ["a", "b"]


@pytest.mark.asyncio
async def test_hook_error_is_suppressed():
    """A hook that raises must not propagate; subsequent hooks still run."""
    subsequent_calls: list[bool] = []

    async def bad_hook(ctx):
        raise ValueError("intentional failure")

    async def good_hook(ctx):
        subsequent_calls.append(True)

    register_hook(bad_hook)
    register_hook(good_hook)

    await run_hooks(HookContext("s", "t", {}))  # must not raise

    assert subsequent_calls == [True]


# ---------------------------------------------------------------------------
# unregister_hook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unregister_hook_prevents_future_calls():
    calls: list[bool] = []

    async def once_hook(ctx):
        calls.append(True)

    register_hook(once_hook)
    unregister_hook(once_hook)
    await run_hooks(HookContext("s", "t", {}))

    assert calls == []


def test_unregister_unknown_hook_is_noop():
    async def phantom(ctx):
        pass  # never registered

    unregister_hook(phantom)  # must not raise


# ---------------------------------------------------------------------------
# reset_hooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_hooks_removes_all_custom_hooks():
    async def custom(ctx):
        pass

    register_hook(custom)
    assert custom in _hooks

    reset_hooks()
    assert custom not in _hooks


@pytest.mark.asyncio
async def test_reset_hooks_preserves_default_log_hook():
    from app.hooks import _log_hook

    reset_hooks()
    assert _log_hook in _hooks
    assert len(_hooks) == 1
