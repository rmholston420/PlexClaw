from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app import runtime_sdk as runtime
from app.main import app


def test_runtime_diag_empty():
    client = TestClient(app)
    resp = client.get("/api/diag/runtime")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "protocol_version" in data
    assert data["live_session_count"] == 0
    assert data["sessions"] == []


def test_runtime_diag_includes_live_session():
    client = TestClient(app)
    create_resp = client.post(
        "/api/sessions",
        json={"model": "claude-sonnet-4-5", "provider": "cloud"},
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    session = runtime.get_session(session_id)
    assert session is not None
    session.last_activity_at = time.monotonic() - 12.345

    resp = client.get("/api/diag/runtime")
    assert resp.status_code == 200
    data = resp.json()

    assert data["live_session_count"] == 1
    assert "websocket_session_count" in data
    assert len(data["sessions"]) == 1

    item = data["sessions"][0]
    assert item["session_id"] == session_id
    assert item["model"] == "claude-sonnet-4-5"
    assert item["provider"] == "cloud"
    assert item["connections"] == 0
    assert item["idle_seconds"] >= 12.0
    assert "status" in item
    assert "mock_mode" in item
