from __future__ import annotations

import time

import pytest

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


@pytest.mark.asyncio
async def test_reap_idle_sessions_skips_recent_session(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session.status = "ready"
    session.last_activity_at = time.monotonic() - 30

    reaped = await runtime.reap_idle_sessions(now=time.monotonic())

    assert reaped == []
    assert runtime.get_session(session.id) is not None


@pytest.mark.asyncio
async def test_reap_idle_sessions_skips_session_with_active_connection(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session.status = "ready"
    session.last_activity_at = time.monotonic() - 120

    monkeypatch.setattr(runtime.ws_manager, "connection_count", lambda _sid: 1)

    reaped = await runtime.reap_idle_sessions(now=time.monotonic())

    assert reaped == []
    assert runtime.get_session(session.id) is not None


@pytest.mark.asyncio
async def test_reap_idle_sessions_uses_monotonic_when_now_is_none(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "60")

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session.status = "ready"
    session.last_activity_at = 100.0

    monkeypatch.setattr("app.runtime_sdk.time.monotonic", lambda: 1000.0)

    reaped = await runtime.reap_idle_sessions()

    assert session.id in reaped
    assert runtime.get_session(session.id) is None


def test_get_idle_timeout_seconds_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "not-a-number")
    assert runtime.get_idle_timeout_seconds() == 1800.0


def test_get_idle_timeout_seconds_has_minimum_floor(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_IDLE_TIMEOUT_SECONDS", "12")
    assert runtime.get_idle_timeout_seconds() == 60.0


def test_get_reap_interval_seconds_invalid_env_falls_back(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_REAP_INTERVAL_SECONDS", "not-a-number")
    assert runtime.get_reap_interval_seconds() == 60.0


def test_get_reap_interval_seconds_has_minimum_floor(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_SESSION_REAP_INTERVAL_SECONDS", "1")
    assert runtime.get_reap_interval_seconds() == 5.0


@pytest.mark.asyncio
async def test_approve_tool_call_rejects_missing_session():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime.approve_tool_call("missing", "tool-1")


@pytest.mark.asyncio
async def test_reject_tool_call_rejects_missing_session():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime.reject_tool_call("missing", "tool-1")
