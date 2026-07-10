from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.event_store as event_store
from app import runtime_sdk as runtime
from app.event_store import init_db
from app.main import app
from app.schemas import SessionCreateRequest


class DummyClient:
    async def interrupt(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_runtime_sessions(tmp_path, monkeypatch):
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


@pytest.mark.asyncio
async def test_delete_session_removes_live_session():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()

    assert runtime.get_session(session.id) is not None

    await runtime.delete_session(session.id)

    assert runtime.get_session(session.id) is None


@pytest.mark.asyncio
async def test_delete_session_clears_context_and_client():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()
    session.context_files["notes.txt"] = "hello"
    session._pending_tool_id = "tool-1"
    session._pending_tool_name = "bash"
    session._pending_tool_input = {"cmd": "pwd"}
    session._approval_decision = "approve"
    session._context_injected = True

    await runtime.delete_session(session.id)

    assert runtime.get_session(session.id) is None


def test_delete_session_route_404_for_missing(client):
    response = client.delete("/api/sessions/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_route_ok(client):
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()

    response = client.delete(f"/api/sessions/{session.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert runtime.get_session(session.id) is None
