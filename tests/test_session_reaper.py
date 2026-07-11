from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


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


@pytest.mark.asyncio
async def test_reap_idle_sessions_logs_idle_reap(monkeypatch, caplog):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")
    req = SessionCreateRequest(
        model="claude-sonnet-4-5",
        provider="cloud",
        permission_mode="auto",
    )
    session = await runtime.create_session(req)
    session.status = "ready"
    session.last_activity_at = time.monotonic() - 120

    with caplog.at_level("INFO"):
        reaped = await runtime.reap_idle_sessions(now=time.monotonic())

    assert session.id in reaped
    assert any(
        "Reaping idle live session" in record.message and session.id in record.message
        for record in caplog.records
    )



@pytest.mark.asyncio
async def test_session_reaper_loop_logs_and_continues_after_reap_error(
    monkeypatch, caplog
):
    from app.main import _session_reaper_loop

    stop_reaper = asyncio.Event()
    calls: list[str] = []

    async def _fake_reap_idle_sessions(now=None):
        calls.append("reap")
        if len(calls) == 1:
            raise RuntimeError("boom")
        stop_reaper.set()
        return []

    async def _fake_wait_for(awaitable, timeout):
        if stop_reaper.is_set():
            return await awaitable
        awaitable.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(runtime, "reap_idle_sessions", _fake_reap_idle_sessions)
    monkeypatch.setattr(runtime, "get_reap_interval_seconds", lambda: 0.01)
    monkeypatch.setattr(asyncio, "wait_for", _fake_wait_for)

    with caplog.at_level("WARNING"):
        await _session_reaper_loop(stop_reaper)

    assert calls == ["reap", "reap"]
    assert any(
        "session reaper loop error: boom" in record.getMessage()
        for record in caplog.records
    )



def test_app_lifespan_starts_and_stops_session_reaper_task(monkeypatch) -> None:
    from app.main import app

    created: list[object] = []

    class _FakeTask:
        def __init__(self) -> None:
            self.cancel_called = False
            self.awaited = False

        def cancel(self) -> None:
            self.cancel_called = True

        def __await__(self):
            async def _done():
                self.awaited = True
                raise asyncio.CancelledError()

            return _done().__await__()

    def _fake_create_task(coro):
        coro.close()
        task = _FakeTask()
        created.append(task)
        return task

    monkeypatch.setattr("app.main.asyncio.create_task", _fake_create_task)

    with TestClient(app):
        assert len(created) == 1
        task = created[0]
        assert task.cancel_called is False
        assert task.awaited is False

    task = created[0]
    assert task.cancel_called is True
    assert task.awaited is True
