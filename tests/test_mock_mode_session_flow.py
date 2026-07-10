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
        assert "Prompt received" in str(first["payload"].get("text", "")) or "Prompt received" in str(first["payload"].get("message", ""))

        second = websocket.receive_json()
        assert second["type"] == "assistant.completed"
        assert second["session_id"] == session_id
        assert second["protocol_version"] == PROTOCOL_VERSION
