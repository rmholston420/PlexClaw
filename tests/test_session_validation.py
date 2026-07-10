from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.event_store as event_store
from app import runtime_sdk as runtime
from app.event_store import init_db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_runtime_and_db(tmp_path, monkeypatch):
    runtime._sessions.clear()
    old_available = runtime._SDK_AVAILABLE
    runtime._SDK_AVAILABLE = True

    db_path = tmp_path / "events.db"
    monkeypatch.setattr(event_store, "DB_PATH", db_path)
    monkeypatch.setattr(event_store, "_conn", None)
    monkeypatch.setattr(event_store, "_conn_path", None)
    monkeypatch.setattr(event_store, "_fts_available", None)
    init_db()

    yield

    runtime._sessions.clear()
    runtime._SDK_AVAILABLE = old_available

    conn = getattr(event_store, "_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    event_store._conn = None
    event_store._conn_path = None
    event_store._fts_available = None


def test_create_session_rejects_invalid_provider(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "bogus",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 422


def test_create_session_rejects_invalid_permission_mode(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "dangerous",
        },
    )

    assert response.status_code == 422


def test_create_session_rejects_blank_model(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "   ",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 422


def test_create_session_accepts_trimmed_model(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "  claude-sonnet-4-5  ",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "created"
    assert "session_id" in body
    assert "mock_mode" in body
    assert isinstance(body["mock_mode"], bool)
