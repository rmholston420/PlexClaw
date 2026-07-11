from __future__ import annotations

import pytest

from app import runtime_sdk as runtime
from app.schemas import SessionCreateRequest


class DummyAssistantMessage:
    def __init__(self, content):
        self.content = content


class DummyResultMessage:
    def __init__(self, subtype=None, stop_reason=None, usage=None):
        self.subtype = subtype
        self.stop_reason = stop_reason
        self.usage = usage


class DummyTextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class BadMappingUsage:
    def keys(self):
        return ["bad"]

    def __getitem__(self, key):
        raise RuntimeError("boom")


class InterruptClientNoDrain:
    def __init__(self):
        self.interrupt_called = False
        self.receive_called = False

    async def interrupt(self):
        self.interrupt_called = True

    async def receive_response(self):
        self.receive_called = True
        if False:
            yield None


class InterruptClientDrainRaises:
    def __init__(self):
        self.interrupt_called = False

    async def interrupt(self):
        self.interrupt_called = True

    async def receive_response(self):
        raise RuntimeError("drain boom")
        yield


@pytest.mark.asyncio
async def test_handle_terminal_unknown_message_returns_false(
    monkeypatch,
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime, "_emit", fake_emit)
    monkeypatch.setattr(runtime, "AssistantMessage", DummyAssistantMessage)
    monkeypatch.setattr(runtime, "ResultMessage", DummyResultMessage)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    handled = await runtime._handle_sdk_terminal_message(
        session,
        object(),
        {},
        allow_completed=True,
    )

    assert handled is False
    assert emitted == []


@pytest.mark.asyncio
async def test_handle_terminal_result_disallowed_emits_nothing(
    monkeypatch,
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime, "_emit", fake_emit)
    monkeypatch.setattr(runtime, "ResultMessage", DummyResultMessage)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    handled = await runtime._handle_sdk_terminal_message(
        session,
        DummyResultMessage(
            stop_reason="end_turn",
            usage={"output_tokens": 3},
        ),
        {},
        allow_completed=False,
    )

    assert handled is True
    assert emitted == []


@pytest.mark.asyncio
async def test_handle_terminal_result_usage_fallback_to_empty_dict(
    monkeypatch,
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime, "_emit", fake_emit)
    monkeypatch.setattr(runtime, "ResultMessage", DummyResultMessage)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    handled = await runtime._handle_sdk_terminal_message(
        session,
        DummyResultMessage(
            stop_reason="end_turn",
            usage=BadMappingUsage(),
        ),
        {},
        allow_completed=True,
    )

    assert handled is True
    assert len(emitted) == 1
    env = emitted[0]
    assert env.type == "assistant.completed"
    assert env.payload["stop_reason"] == "end_turn"
    assert env.payload["usage"] == {}


@pytest.mark.asyncio
async def test_interrupt_session_missing_session_raises_keyerror():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime.interrupt_session("missing")


@pytest.mark.asyncio
async def test_interrupt_session_mock_mode_skips_drain(
    monkeypatch,
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime, "_emit", fake_emit)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    client = InterruptClientNoDrain()
    session._client = client
    session.mock_mode = True
    session.status = "running"

    await runtime.interrupt_session(session.id)

    assert client.interrupt_called is True
    assert client.receive_called is False
    assert session.status == "interrupted"
    assert len(emitted) == 1
    assert emitted[0].type == "session.interrupted"
    assert emitted[0].payload == {"reason": "user_interrupt"}


@pytest.mark.asyncio
async def test_interrupt_session_logs_warning_and_still_emits(
    monkeypatch,
    caplog,
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime, "_emit", fake_emit)

    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    emitted.clear()

    session._client = InterruptClientDrainRaises()
    session.mock_mode = False
    session.status = "running"

    with caplog.at_level("WARNING"):
        await runtime.interrupt_session(session.id)

    assert session.status == "interrupted"
    assert len(emitted) == 1
    assert emitted[0].type == "session.interrupted"
    assert any(
        "Interrupt drain error: drain boom" in r.getMessage()
        for r in caplog.records
    )
