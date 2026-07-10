from __future__ import annotations

import time

import pytest

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


@pytest.fixture(autouse=True)
def clear_sessions():
    runtime._sessions.clear()
    yield
    runtime._sessions.clear()


@pytest.mark.asyncio
async def test_reap_idle_sessions_removes_old_disconnected_ready_session(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")
    req = SessionCreateRequest(
        model="claude-sonnet-4-5",
        provider="cloud",
        permission_mode="auto",
    )
    session = await runtime.create_session(req)
    session.status = "ready"
    session.last_activity_at = time.monotonic() - 120

    reaped = await runtime.reap_idle_sessions(now=time.monotonic())

    assert session.id in reaped
    assert runtime.get_session(session.id) is None


@pytest.mark.asyncio
async def test_reap_idle_sessions_keeps_running_session(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")
    req = SessionCreateRequest(
        model="claude-sonnet-4-5",
        provider="cloud",
        permission_mode="auto",
    )
    session = await runtime.create_session(req)
    session.status = "running"
    session.last_activity_at = time.monotonic() - 120

    reaped = await runtime.reap_idle_sessions(now=time.monotonic())

    assert reaped == []
    assert runtime.get_session(session.id) is not None


@pytest.mark.asyncio
async def test_touch_session_refreshes_last_activity():
    req = SessionCreateRequest(
        model="claude-sonnet-4-5",
        provider="cloud",
        permission_mode="auto",
    )
    session = await runtime.create_session(req)
    old = session.last_activity_at
    session.last_activity_at = old - 100

    runtime.touch_session(session)

    assert session.last_activity_at > old
