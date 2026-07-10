from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import runtime_sdk as runtime
from app.main import app
from app.normalizer import normalize_tool_permission_decided
from app.schemas import PROTOCOL_VERSION, SessionCreateRequest


def test_normalize_tool_permission_decided_shape():
    evt = normalize_tool_permission_decided(
        "s1",
        7,
        "tool-1",
        "bash",
        {"cmd": "pwd"},
        "approve",
    )
    assert evt.type == "tool.permission_decided"
    assert evt.session_id == "s1"
    assert evt.seq == 7
    assert evt.payload == {
        "tool_id": "tool-1",
        "tool_name": "bash",
        "tool_input": {"cmd": "pwd"},
        "decision": "approve",
    }


@pytest.mark.asyncio
async def test_approve_tool_call_emits_permission_decided(monkeypatch):
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
    session.pending_approvals["tool-1"] = runtime.PendingApproval(
        tool_id="tool-1",
        tool_name="bash",
        tool_input={"cmd": "pwd"},
    )

    await runtime.approve_tool_call(session.id, "tool-1")

    assert session.pending_approvals["tool-1"].decision == "approve"
    assert session._approval_event.is_set()
    evt = emitted[-1]
    assert evt.type == "tool.permission_decided"
    assert evt.payload["tool_id"] == "tool-1"
    assert evt.payload["tool_name"] == "bash"
    assert evt.payload["tool_input"] == {"cmd": "pwd"}
    assert evt.payload["decision"] == "approve"


@pytest.mark.asyncio
async def test_reject_tool_call_emits_permission_decided(monkeypatch):
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
    session.pending_approvals["tool-1"] = runtime.PendingApproval(
        tool_id="tool-1",
        tool_name="bash",
        tool_input={"cmd": "pwd"},
    )

    await runtime.reject_tool_call(session.id, "tool-1")

    assert session.pending_approvals["tool-1"].decision == "reject"
    assert session._approval_event.is_set()
    evt = emitted[-1]
    assert evt.type == "tool.permission_decided"
    assert evt.payload["tool_id"] == "tool-1"
    assert evt.payload["tool_name"] == "bash"
    assert evt.payload["tool_input"] == {"cmd": "pwd"}
    assert evt.payload["decision"] == "reject"


def test_websocket_approval_messages_emit_permission_decided_events():
    client = TestClient(app)

    create = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    with client.websocket_connect(
        f"/ws/{session_id}?protocol_version={PROTOCOL_VERSION}"
    ) as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "session.ready"

        session = runtime.get_session(session_id)
        assert session is not None

        session.pending_approvals["tool-a"] = runtime.PendingApproval(
            tool_id="tool-a",
            tool_name="bash",
            tool_input={"cmd": "pwd"},
        )

        websocket.send_json({"type": "approve", "tool_id": "tool-a"})
        msg = websocket.receive_json()
        while msg["type"] != "tool.permission_decided":
            msg = websocket.receive_json()
        assert msg["payload"]["tool_id"] == "tool-a"
        assert msg["payload"]["decision"] == "approve"

        assert session.pending_approvals["tool-a"].event.is_set() is True
        session._approval_decision = None
        session.pending_approvals["tool-b"] = runtime.PendingApproval(
            tool_id="tool-b",
            tool_name="read",
            tool_input={"path": "README.md"},
        )

        websocket.send_json({"type": "reject", "tool_id": "tool-b"})
        msg = websocket.receive_json()
        while msg["type"] != "tool.permission_decided":
            msg = websocket.receive_json()
        assert msg["payload"]["tool_id"] == "tool-b"
        assert msg["payload"]["decision"] == "reject"
