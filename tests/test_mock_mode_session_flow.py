from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PROTOCOL_VERSION


def test_mock_mode_session_create_and_websocket_prompt_flow() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )
    assert create.status_code == 200, create.text
    data = create.json()
    session_id = data["session_id"]
    assert session_id
    assert data["status"] == "created"
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["model"] == "claude-sonnet-4-5"
    assert data["provider"] == "cloud"

    replay = client.get(f"/api/sessions/{session_id}/replay")
    assert replay.status_code == 200, replay.text
    events = replay.json()
    created = next(
        evt
        for evt in events
        if evt["type"] == "system.message"
        and evt["payload"].get("subtype") == "session.created"
    )
    assert "mock_mode" in created["payload"]
    assert isinstance(created["payload"]["mock_mode"], bool)
    assert created["payload"]["model"] == data["model"]
    assert created["payload"]["provider"] == data["provider"]

    with client.websocket_connect(
        f"/ws/{session_id}?protocol_version={PROTOCOL_VERSION}"
    ) as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "session.ready"
        assert "mock_mode" in ready["payload"]
        assert isinstance(ready["payload"]["mock_mode"], bool)
        assert ready["payload"]["model"]
        assert ready["session_id"] == session_id
        assert ready["protocol_version"] == PROTOCOL_VERSION

        prompt = f"mock-flow-{uuid.uuid4()}"
        websocket.send_json({"prompt": prompt})

        first = websocket.receive_json()
        assert first["type"] == "system.message"
        assert first["session_id"] == session_id
        assert (
            "Prompt received" in str(first["payload"].get("text", ""))
            or "Prompt received" in str(first["payload"].get("message", ""))
        )

        second = websocket.receive_json()
        assert second["type"] == "assistant.completed"
        assert second["session_id"] == session_id
        assert second["protocol_version"] == PROTOCOL_VERSION


import asyncio

from app import runtime_sdk as rs


class _FakeResultUsage(dict):
    pass


class _FakeResultMessage:
    def __init__(self, subtype="end_turn", usage=None):
        self.subtype = subtype
        self.usage = usage or _FakeResultUsage(output_tokens=1)


class _FakeClientWithResult:
    async def connect(self):
        return None

    async def query(self, prompt: str):
        return None

    async def receive_response(self):
        yield rs.MockStreamEvent(
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "hello"},
            }
        )
        yield _FakeResultMessage()


async def _collect_emitted_types_for_real_result_path():
    session = rs.LiveSession(
        id="test-session",
        created_at="now",
        model="claude-sonnet-4-5",
        provider="cloud",
        cwd=None,
        permission_mode="manual",
        protocol_version=rs.PROTOCOL_VERSION,
        mock_mode=False,
    )
    session._client = _FakeClientWithResult()

    emitted = []

    async def _fake_emit(session, env):
        emitted.append(env.type)

    original_emit = rs._emit
    original_result = rs.ResultMessage
    try:
        rs._emit = _fake_emit
        rs.ResultMessage = _FakeResultMessage
        await rs._stream_sdk(session, "hello")
    finally:
        rs._emit = original_emit
        rs.ResultMessage = original_result

    return emitted


def test_stream_sdk_emits_single_assistant_completed_when_result_message_arrives():
    emitted = asyncio.run(_collect_emitted_types_for_real_result_path())
    assert emitted.count("assistant.completed") == 1
    assert emitted.count("assistant.delta") == 1
