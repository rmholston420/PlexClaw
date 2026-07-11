from __future__ import annotations

import asyncio
import uuid

from fastapi.testclient import TestClient

from app import runtime_sdk as rs
from app.main import app
from app.schemas import PROTOCOL_VERSION


def test_mock_mode_session_create_and_websocket_prompt_flow() -> None:
    client = TestClient(app)

    create = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )
    assert create.status_code == 200, create.text
    data = create.json()
    session_id = data["session_id"]
    assert session_id
    assert data["status"] == "created"
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["model"] == "claude-sonnet-4-5"
    assert data["provider"] == "cloud"

    replay = client.get(f"/api/sessions/{session_id}/replay")
    assert replay.status_code == 200, replay.text
    events = replay.json()
    created = next(
        evt
        for evt in events
        if evt["type"] == "system.message"
        and evt["payload"].get("subtype") == "session.created"
    )
    assert "mock_mode" in created["payload"]
    assert isinstance(created["payload"]["mock_mode"], bool)
    assert created["payload"]["model"] == data["model"]
    assert created["payload"]["provider"] == data["provider"]

    with client.websocket_connect(
        f"/ws/{session_id}?protocol_version={PROTOCOL_VERSION}"
    ) as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "session.ready"
        assert "mock_mode" in ready["payload"]
        assert isinstance(ready["payload"]["mock_mode"], bool)
        assert ready["payload"]["model"]
        assert ready["session_id"] == session_id
        assert ready["protocol_version"] == PROTOCOL_VERSION

        replay_after_ready = client.get(f"/api/sessions/{session_id}/replay")
        assert replay_after_ready.status_code == 200, replay_after_ready.text
        replay_events = replay_after_ready.json()
        replay_ready = next(
            evt for evt in replay_events if evt["type"] == "session.ready"
        )
        assert replay_ready["session_id"] == session_id
        assert "mock_mode" in replay_ready["payload"]
        assert isinstance(replay_ready["payload"]["mock_mode"], bool)

        prompt = f"mock-flow-{uuid.uuid4()}"
        websocket.send_json({"prompt": prompt})

        first = websocket.receive_json()
        assert first["type"] == "system.message"
        assert first["session_id"] == session_id
        assert (
            "Prompt received" in str(first["payload"].get("text", ""))
            or "Prompt received" in str(first["payload"].get("message", ""))
        )

        second = websocket.receive_json()
        assert second["type"] == "assistant.completed"
        assert second["session_id"] == session_id
        assert second["protocol_version"] == PROTOCOL_VERSION


class _FakeResultUsage(dict):
    pass


class _FakeResultMessage:
    def __init__(self, subtype: str = "end_turn", usage=None) -> None:
        self.subtype = subtype
        self.usage = usage or _FakeResultUsage(output_tokens=1)


class _FakeClientWithResult:
    async def connect(self) -> None:
        return None

    async def query(self, prompt: str) -> None:
        return None

    async def receive_response(self):
        yield rs.MockStreamEvent(
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "hello"},
            }
        )
        yield _FakeResultMessage()


async def _collect_emitted_types_for_real_result_path() -> list[str]:
    session = rs.LiveSession(
        id="test-session",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=False,
    )
    session._client = _FakeClientWithResult()

    emitted: list[str] = []

    async def _fake_emit(_session, env) -> None:
        emitted.append(env.type)

    original_emit = rs._emit
    original_result = rs.ResultMessage
    try:
        rs._emit = _fake_emit
        rs.ResultMessage = _FakeResultMessage
        await rs._stream_sdk(session, "hello")
    finally:
        rs._emit = original_emit
        rs.ResultMessage = original_result

    return emitted


def test_stream_sdk_emits_single_assistant_completed_when_result_message_arrives(
) -> None:
    emitted = asyncio.run(_collect_emitted_types_for_real_result_path())
    assert emitted.count("assistant.completed") == 1
    assert emitted.count("assistant.delta") == 1


class _FakeClientThatFails:
    async def connect(self) -> None:
        return None

    async def query(self, prompt: str) -> None:
        return None

    async def receive_response(self):
        if False:
            yield None
        raise RuntimeError("boom")


async def _collect_emitted_types_for_failed_result_path() -> tuple[list[str], str]:
    session = rs.LiveSession(
        id="failed-session",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=False,
    )
    session._client = _FakeClientThatFails()

    emitted: list[str] = []

    async def _fake_emit(_session, env) -> None:
        emitted.append(env.type)

    original_emit = rs._emit
    try:
        rs._emit = _fake_emit
        try:
            await rs._stream_sdk(session, "hello")
        except RuntimeError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("Expected _stream_sdk to re-raise RuntimeError")
    finally:
        rs._emit = original_emit

    return emitted, session.status


def test_stream_sdk_failed_session_emits_failed_without_completed() -> None:
    emitted, status = asyncio.run(_collect_emitted_types_for_failed_result_path())
    assert "session.failed" in emitted
    assert "assistant.completed" not in emitted
    assert status == "failed"



class _FakeInterruptibleClient:
    def __init__(self) -> None:
        self._interrupted = False

    async def connect(self) -> None:
        return None

    async def query(self, prompt: str) -> None:
        return None

    async def interrupt(self) -> None:
        self._interrupted = True

    async def receive_response(self):
        yield rs.MockStreamEvent(
            {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "partial"},
            }
        )
        while not self._interrupted:
            await asyncio.sleep(0.01)


async def _collect_emitted_types_for_interrupted_turn() -> tuple[list[str], str]:
    session = rs.LiveSession(
        id="interrupted-session",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    session._client = _FakeInterruptibleClient()
    rs._sessions[session.id] = session

    emitted: list[str] = []

    async def _fake_emit(_session, env) -> None:
        emitted.append(env.type)

    original_emit = rs._emit
    try:
        rs._emit = _fake_emit
        stream_task = asyncio.create_task(rs.submit_prompt(session.id, "hello"))

        for _ in range(50):
            if "assistant.delta" in emitted:
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError(
                "Timed out waiting for assistant.delta before "
                "interrupt"
            )

        await rs.interrupt_session(session.id)
        await stream_task
    finally:
        rs._emit = original_emit
        rs._sessions.pop(session.id, None)

    return emitted, session.status


def test_interrupt_session_emits_interrupted_without_completed_for_cancelled_turn(
) -> None:
    emitted, status = asyncio.run(_collect_emitted_types_for_interrupted_turn())
    assert "assistant.delta" in emitted
    assert "session.interrupted" in emitted
    assert "assistant.completed" not in emitted
    assert status == "interrupted"



class _FakeManualRejectClient:
    def __init__(self) -> None:
        self.interrupted = False

    async def connect(self) -> None:
        return None

    async def query(self, prompt: str) -> None:
        return None

    async def interrupt(self) -> None:
        self.interrupted = True

    async def receive_response(self):
        yield rs.MockStreamEvent(
            {
                "type": "content_block_start",
                "content_block": {
                    "type": "tool_use",
                    "id": "tool-1",
                    "name": "bash",
                },
            }
        )
        yield rs.MockStreamEvent(
            {
                "type": "content_block_delta",
                "delta": {
                    "type": "input_json_delta",
                    "partial_json": '{"cmd":"echo hi"}',
                },
            }
        )
        yield rs.MockStreamEvent({"type": "content_block_stop"})
        while not self.interrupted:
            await asyncio.sleep(0.01)


async def _collect_emitted_types_for_manual_rejection() -> tuple[list[str], str]:
    session = rs.LiveSession(
        id="rejected-tool-session",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    session._client = _FakeManualRejectClient()

    emitted: list[tuple[str, dict]] = []

    async def _fake_emit(_session, env) -> None:
        emitted.append((env.type, dict(env.payload)))

    original_emit = rs._emit
    original_await_approval = rs._await_tool_approval
    try:
        rs._emit = _fake_emit

        async def _reject(*args, **kwargs) -> bool:
            return False

        rs._await_tool_approval = _reject
        await rs._stream_sdk(session, "hello")
    finally:
        rs._emit = original_emit
        rs._await_tool_approval = original_await_approval

    event_types = [event_type for event_type, _payload in emitted]
    rejected_payloads = [
        payload
        for event_type, payload in emitted
        if event_type == "tool.completed"
    ]

    assert any(payload.get("is_error") is True for payload in rejected_payloads)
    assert any(
        payload.get("output", {}).get("status") == "rejected"
        for payload in rejected_payloads
    )

    return event_types, session.status


def test_manual_tool_rejection_emits_rejection_without_completed() -> None:
    emitted, status = asyncio.run(_collect_emitted_types_for_manual_rejection())
    assert "tool.started" in emitted
    assert "tool.delta" in emitted
    assert "tool.completed" in emitted
    assert "assistant.completed" not in emitted
    assert status == "interrupted"



async def _collect_reaped_ids_for_idle_session() -> tuple[list[str], bool]:
    session = rs.LiveSession(
        id="idle-session",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    session.status = "ready"
    session.last_activity_at = 0.0
    rs._sessions[session.id] = session

    try:
        reaped = await rs.reap_idle_sessions(now=10_000.0)
        still_present = session.id in rs._sessions
    finally:
        rs._sessions.pop(session.id, None)

    return reaped, still_present


def test_reap_idle_sessions_reaps_only_live_entries() -> None:
    reaped, still_present = asyncio.run(_collect_reaped_ids_for_idle_session())
    assert reaped == ["idle-session"]
    assert still_present is False
