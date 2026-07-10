from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_mod
from app.main import app


def test_live_replay_endpoint_returns_canonical_events(monkeypatch):
    def fake_query_events(session_id: str):
        assert session_id == "live-1"
        return [
            {
                "type": "assistant.delta",
                "session_id": "live-1",
                "seq": 1,
                "payload": {"text": "hello"},
                "protocol_version": "0.2.0",
            },
            {
                "type": "assistant.completed",
                "session_id": "live-1",
                "seq": 2,
                "payload": {"stop_reason": "end_turn", "usage": {}},
                "protocol_version": "0.2.0",
            },
        ]

    monkeypatch.setattr(main_mod, "query_events", fake_query_events)

    with TestClient(app) as client:
        resp = client.get("/api/sessions/live-1/replay")

    assert resp.status_code == 200
    data = resp.json()
    assert [evt["type"] for evt in data] == [
        "assistant.delta",
        "assistant.completed",
    ]
    assert data[0]["protocol_version"] == "0.2.0"


def test_archive_replay_endpoint_returns_canonical_events(monkeypatch):
    async def fake_get_archive_replay_events(session_id: str):
        assert session_id == "arch-1"
        return [
            {
                "type": "tool.started",
                "session_id": "arch-1",
                "seq": 1,
                "payload": {
                    "tool_id": "t1",
                    "tool_name": "Write",
                    "tool_input": {},
                },
                "protocol_version": "0.2.0",
            },
            {
                "type": "tool.delta",
                "session_id": "arch-1",
                "seq": 2,
                "payload": {
                    "tool_id": "t1",
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/x.txt"},
                    "partial": "",
                },
                "protocol_version": "0.2.0",
            },
            {
                "type": "assistant.completed",
                "session_id": "arch-1",
                "seq": 3,
                "payload": {"stop_reason": "tool_use", "usage": {}},
                "protocol_version": "0.2.0",
            },
        ]

    monkeypatch.setattr(
        main_mod.runtime,
        "get_archive_replay_events",
        fake_get_archive_replay_events,
    )

    with TestClient(app) as client:
        resp = client.get("/api/archive/sessions/arch-1/replay")

    assert resp.status_code == 200
    data = resp.json()
    assert [evt["type"] for evt in data] == [
        "tool.started",
        "tool.delta",
        "assistant.completed",
    ]
    for evt in data:
        assert evt["session_id"] == "arch-1"
        assert isinstance(evt["seq"], int)
        assert isinstance(evt["payload"], dict)
        assert evt["protocol_version"] == "0.2.0"
