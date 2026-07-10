from __future__ import annotations

import asyncio

import pytest

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


@pytest.mark.asyncio
async def test_approve_tool_call_rejects_wrong_tool_id():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session.pending_approvals["tool-1"] = runtime.PendingApproval(
        tool_id="tool-1",
        tool_name="bash",
        tool_input={"cmd": "pwd"},
    )

    with pytest.raises(KeyError):
        await runtime.approve_tool_call(session.id, "wrong-tool")


@pytest.mark.asyncio
async def test_reject_tool_call_rejects_wrong_tool_id():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session.pending_approvals["tool-1"] = runtime.PendingApproval(
        tool_id="tool-1",
        tool_name="bash",
        tool_input={"cmd": "pwd"},
    )

    with pytest.raises(KeyError):
        await runtime.reject_tool_call(session.id, "wrong-tool")


@pytest.mark.asyncio
async def test_await_tool_approval_clears_state_after_approve(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr("app.runtime_sdk._emit", fake_emit)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    async def approve_later():
        await asyncio.sleep(0)
        await runtime.approve_tool_call(session.id, "tool-1")

    task = asyncio.create_task(
        runtime._await_tool_approval(
            session,
            "tool-1",
            "bash",
            {"cmd": "pwd"},
        )
    )
    asyncio.create_task(approve_later())
    approved = await task

    assert approved is True
    assert session.pending_approvals == {}
    assert session.pending_tool_name is None
    assert session.pending_tool_input is None
    assert all(p.decision is None for p in session.pending_approvals.values())
    evt = next(e for e in emitted if e.type == "tool.permission_required")
    assert evt.payload["tool_id"] == "tool-1"
    assert evt.payload["tool_name"] == "bash"
    assert evt.payload["tool_input"] == {"cmd": "pwd"}
    assert evt.payload["status"] == "pending"


@pytest.mark.asyncio
async def test_await_tool_approval_clears_state_after_reject(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr("app.runtime_sdk._emit", fake_emit)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    async def reject_later():
        await asyncio.sleep(0)
        await runtime.reject_tool_call(session.id, "tool-1")

    task = asyncio.create_task(
        runtime._await_tool_approval(
            session,
            "tool-1",
            "bash",
            {"cmd": "pwd"},
        )
    )
    asyncio.create_task(reject_later())
    approved = await task

    assert approved is False
    assert session.pending_approvals == {}
    assert session.pending_tool_name is None
    assert session.pending_tool_input is None
    assert all(p.decision is None for p in session.pending_approvals.values())
    evt = next(e for e in emitted if e.type == "tool.permission_required")
    assert evt.payload["tool_id"] == "tool-1"
    assert evt.payload["tool_name"] == "bash"
    assert evt.payload["tool_input"] == {"cmd": "pwd"}
    assert evt.payload["status"] == "pending"
