from __future__ import annotations

import pytest

import app.runtime_sdk as runtime_sdk
from app.runtime_sdk import LiveSession, _handle_sdk_terminal_message


@pytest.fixture
def clean_sessions():
    runtime_sdk._sessions.clear()
    yield
    runtime_sdk._sessions.clear()


def make_session(session_id: str = "sess-uncovered", **kwargs):
    return LiveSession(
        id=session_id,
        model=kwargs.get("model", "claude-sonnet-4-5"),
        cwd=kwargs.get("cwd"),
        provider=kwargs.get("provider", "cloud"),
        permission_mode=kwargs.get("permission_mode", "manual"),
        resume_session_id=kwargs.get("resume_session_id"),
        fork_session=kwargs.get("fork_session", False),
        mock_mode=kwargs.get("mock_mode", True),
    )


@pytest.mark.asyncio
async def test_update_session_invalid_sdk_permission_mode_raises(clean_sessions):
    session = make_session()
    runtime_sdk._sessions[session.id] = session

    with pytest.raises(ValueError, match="invalid sdk_permission_mode: nope"):
        await runtime_sdk.update_session(
            session.id,
            sdk_permission_mode="nope",
        )


@pytest.mark.asyncio
async def test_handle_sdk_terminal_message_usage_dict_failure_falls_back_empty(
    monkeypatch, clean_sessions
):
    session = make_session(mock_mode=False)
    runtime_sdk._sessions[session.id] = session

    class BadUsage:
        def __iter__(self):
            raise TypeError("boom")

    ResultType = type("ResultMessage", (), {})
    msg = ResultType()
    msg.subtype = "end_turn"
    msg.usage = BadUsage()

    emitted = []

    async def fake_emit(_session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    monkeypatch.setattr(runtime_sdk, "ResultMessage", ResultType)

    handled = await _handle_sdk_terminal_message(
        session,
        msg,
        {},
        allow_completed=True,
    )

    assert handled is True
    assert emitted[-1].type == "assistant.completed"
    assert emitted[-1].payload["stop_reason"] == "end_turn"
    assert emitted[-1].payload["usage"] == {}

@pytest.mark.asyncio
async def test_update_session_sets_valid_sdk_permission_mode(clean_sessions):
    session = make_session()
    runtime_sdk._sessions[session.id] = session

    result = await runtime_sdk.update_session(
        session.id,
        sdk_permission_mode="acceptEdits",
    )

    assert result is session
    assert session.sdk_permission_mode == "acceptEdits"

