from __future__ import annotations

import pytest

import app.runtime_sdk as runtime_sdk
from app.runtime_sdk import LiveSession, _handle_sdk_terminal_message, _stream_sdk


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

@pytest.mark.asyncio
async def test_handle_sdk_terminal_message_usage_object_uses_vars(
    monkeypatch, clean_sessions
):
    session = make_session(mock_mode=False)
    runtime_sdk._sessions[session.id] = session

    class GoodUsage:
        def __init__(self):
            self.input_tokens = 11
            self.output_tokens = 22

    ResultType = type("ResultMessage", (), {})
    msg = ResultType()
    msg.subtype = "end_turn"
    msg.usage = GoodUsage()

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
    assert emitted[-1].payload["usage"] == {
        "input_tokens": 11,
        "output_tokens": 22,
    }

@pytest.mark.asyncio
async def test_handle_sdk_terminal_message_usage_mapping_uses_dict(
    monkeypatch, clean_sessions
):
    session = make_session(mock_mode=False)
    runtime_sdk._sessions[session.id] = session

    class MappingUsage:
        __slots__ = ()

        def __iter__(self):
            return iter(
                [
                    ("input_tokens", 33),
                    ("output_tokens", 44),
                ]
            )

    ResultType = type("ResultMessage", (), {})
    msg = ResultType()
    msg.subtype = "end_turn"
    msg.usage = MappingUsage()

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
    assert emitted[-1].payload["usage"] == {
        "input_tokens": 33,
        "output_tokens": 44,
    }

@pytest.mark.asyncio
async def test_stream_sdk_emits_completed_when_no_terminal_result(
    monkeypatch, clean_sessions
):
    session = make_session(session_id="stream-no-result", mock_mode=False)
    runtime_sdk._sessions[session.id] = session

    emitted = []

    async def fake_emit(_session, env):
        emitted.append(env)

    class FakeClient:
        async def connect(self):
            return None

        async def query(self, prompt):
            return None

        async def receive_response(self):
            if False:
                yield None

    session._client = FakeClient()
    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)

    await _stream_sdk(session, "hello")

    assert session.status != "failed"
    assert session.status != "interrupted"
    assert emitted[-1].type == "assistant.completed"
    assert emitted[-1].payload["stop_reason"] == "end_turn"
    assert emitted[-1].payload["usage"] == {}

@pytest.mark.asyncio
async def test_stream_sdk_invalid_tool_json_emits_raw_tool_input(
    monkeypatch, clean_sessions
):
    session = make_session(
        session_id="bad-tool-json",
        mock_mode=True,
        permission_mode="auto",
    )
    runtime_sdk._sessions[session.id] = session

    emitted = []

    async def fake_emit(_session, env):
        emitted.append(env)

    class FakeBadJsonClient:
        async def connect(self):
            return None

        async def query(self, prompt):
            return None

        async def receive_response(self):
            yield runtime_sdk.MockStreamEvent(
                {
                    "type": "content_block_start",
                    "content_block": {
                        "type": "tool_use",
                        "id": "tool-bad-json",
                        "name": "bash",
                    },
                }
            )
            yield runtime_sdk.MockStreamEvent(
                {
                    "type": "content_block_delta",
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": "{bad json",
                    },
                }
            )
            yield runtime_sdk.MockStreamEvent({"type": "content_block_stop"})

    session._client = FakeBadJsonClient()
    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)

    await _stream_sdk(session, "hello")

    tool_delta_events = [env for env in emitted if env.type == "tool.delta"]
    assert tool_delta_events
    assert tool_delta_events[-1].payload["tool_name"] == "bash"
    assert tool_delta_events[-1].payload["tool_input"] == {"_raw": "{bad json"}

