"""Tests for GET /api/sessions (live session list)."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

import app.runtime_sdk as runtime
from app.main import app


def test_list_sessions_empty():
    client = TestClient(app)
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_created_session():
    client = TestClient(app)
    create_resp = client.post(
        "/api/sessions",
        json={"model": "claude-sonnet-4-5", "provider": "cloud"},
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1
    s = sessions[0]
    assert s["session_id"] == session_id
    assert s["model"] == "claude-sonnet-4-5"
    assert s["provider"] == "cloud"
    assert "status" in s
    assert "mock_mode" in s


def test_list_sessions_removed_after_delete():
    client = TestClient(app)
    create_resp = client.post(
        "/api/sessions",
        json={"model": "claude-sonnet-4-5", "provider": "cloud"},
    )
    session_id = create_resp.json()["session_id"]

    client.delete(f"/api/sessions/{session_id}")

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    ids = [s["session_id"] for s in list_resp.json()]
    assert session_id not in ids


def test_list_sessions_includes_connections_and_idle_seconds():
    client = TestClient(app)
    create_resp = client.post(
        "/api/sessions",
        json={"model": "claude-sonnet-4-5", "provider": "cloud"},
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    session = runtime.get_session(session_id)
    assert session is not None
    session.last_activity_at = time.monotonic() - 7.25

    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1

    s = sessions[0]
    assert s["session_id"] == session_id
    assert s["connections"] == 0
    assert s["idle_seconds"] >= 7.0
