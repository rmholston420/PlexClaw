import asyncio

import pytest

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


@pytest.mark.asyncio
async def test_approve_only_resolves_matching_pending_tool(monkeypatch):
    async def fake_emit(session, env):
        return None

    monkeypatch.setattr(runtime, "_emit", fake_emit)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )

    task_a = asyncio.create_task(
        runtime._await_tool_approval(session, "tool-a", "bash", {"cmd": "pwd"})
    )
    task_b = asyncio.create_task(
        runtime._await_tool_approval(session, "tool-b", "read", {"path": "README.md"})
    )

    await asyncio.sleep(0)
    await runtime.approve_tool_call(session.id, "tool-a")
    await asyncio.sleep(0)

    assert task_a.done() is True
    assert task_b.done() is False
    assert await task_a is True

    await runtime.reject_tool_call(session.id, "tool-b")
    await asyncio.sleep(0)

    assert await task_b is False
    assert session.pending_approvals == {}

    await runtime.delete_session(session.id)
