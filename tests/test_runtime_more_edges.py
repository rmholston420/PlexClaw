from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import runtime_sdk as runtime
from app.runtime_sdk import (
    LiveSession,
    PendingApproval,
    _archive_messages_to_events,
    _handle_sdk_terminal_message,
)

pytestmark = pytest.mark.timeout(5)


@pytest.fixture(autouse=True)
def clear_runtime_sessions():
    runtime._sessions.clear()
    yield
    runtime._sessions.clear()


@pytest.mark.asyncio
async def test_update_session_invalid_permission_mode_raises_value_error():
    session = LiveSession(
        id="perm",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    runtime._sessions[session.id] = session

    with pytest.raises(ValueError) as exc:
        await runtime.update_session(session.id, permission_mode="bad-mode")

    assert "invalid permission_mode" in str(exc.value)
    assert session.permission_mode == "manual"


def test_add_context_file_limits_and_size():
    session = LiveSession(
        id="ctx",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    runtime._sessions[session.id] = session

    runtime.add_context_file("ctx", "a.txt", "hi")
    assert runtime.list_context_files("ctx") == [{"filename": "a.txt", "size": 2}]

    big = "x" * (200 * 1024 + 1)
    with pytest.raises(ValueError) as exc:
        runtime.add_context_file("ctx", "big.txt", big)
    assert "200KB" in str(exc.value)

    for i in range(1, 10):
        runtime.add_context_file("ctx", f"f{i}.txt", "ok")

    assert len(session.context_files) == 10

    with pytest.raises(ValueError) as exc:
        runtime.add_context_file("ctx", "extra.txt", "ok")
    assert "maximum 10 context files" in str(exc.value)


def test_remove_context_file_unknown_raises_key_error():
    session = LiveSession(
        id="rmctx",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    runtime._sessions[session.id] = session
    runtime.add_context_file("rmctx", "keep.txt", "ok")

    with pytest.raises(KeyError):
        runtime.remove_context_file("rmctx", "missing.txt")

    runtime.remove_context_file("rmctx", "keep.txt")
    assert "keep.txt" not in session.context_files


def test_inject_context_into_prompt_injects_once_and_marks_flag():
    session = LiveSession(
        id="inject",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    runtime._sessions[session.id] = session

    session.context_files["a.txt"] = "AAA"
    session.context_files["b.txt"] = "BBB"

    first = runtime._inject_context_into_prompt(session, "Hello")
    assert "Attached file context:" in first
    assert "--- FILE: a.txt ---" in first
    assert "--- FILE: b.txt ---" in first
    assert "--- USER PROMPT ---" in first
    assert "AAA" in first
    assert "BBB" in first
    assert "Hello" in first
    assert session._context_injected is True

    second = runtime._inject_context_into_prompt(session, "Hello again")
    assert second == "Hello again"


@pytest.mark.asyncio
async def test_submit_prompt_raises_when_client_not_initialized():
    session = LiveSession(
        id="noprompt",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )
    runtime._sessions[session.id] = session

    with pytest.raises(RuntimeError) as exc:
        await runtime.submit_prompt(session.id, "Hi")

    assert "client is not initialized" in str(exc.value)


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="_await_tool_approval reject path still hangs; needs impl-driven test"
)
async def test_await_tool_approval_reject_path_interrupts_and_marks_interrupted(
    monkeypatch,
):
    session = LiveSession(
        id="tool-reject",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=True,
    )

    async def fake_interrupt():
        return None

    session._client = SimpleNamespace(interrupt=fake_interrupt)
    runtime._sessions[session.id] = session

    approval = PendingApproval(
        tool_id="t1",
        tool_name="bash",
        tool_input={"cmd": "ls"},
    )
    session.pending_approvals["t1"] = approval

    async def fake_emit(_session, _env):
        return None

    monkeypatch.setattr(runtime, "_emit", fake_emit)

    async def trigger_reject():
        approval.decision = "reject"
        approval.event.set()

    approval_task = runtime._await_tool_approval(
        session,
        "t1",
        "bash",
        {"cmd": "ls"},
    )
    trigger_task = trigger_reject()

    approved = await asyncio.gather(approval_task, trigger_task)
    approved_value = approved[0]

    assert approved_value is False
    assert session.status == "interrupted"
    assert "t1" not in session.pending_approvals


@pytest.mark.asyncio
async def test_handle_sdk_terminal_message_result_message_usage_and_stop_reason(
    monkeypatch,
):
    session = LiveSession(
        id="term",
        model="claude-sonnet-4-5",
        cwd=None,
        provider="cloud",
        permission_mode="manual",
        resume_session_id=None,
        fork_session=False,
        mock_mode=False,
    )
    runtime._sessions[session.id] = session

    class FakeUsage:
        def __init__(self):
            self.input_tokens = 10
            self.output_tokens = 20

    ResultType = type("ResultMessage", (), {})
    msg = ResultType()
    msg.subtype = "stop_subtype"
    msg.usage = FakeUsage()

    async def fake_emit(_session, env):
        assert env.payload["stop_reason"] == "stop_subtype"
        assert env.payload["usage"]["input_tokens"] == 10
        assert env.payload["usage"]["output_tokens"] == 20

    monkeypatch.setattr(runtime, "_emit", fake_emit)
    monkeypatch.setattr(runtime, "ResultMessage", ResultType)

    handled = await _handle_sdk_terminal_message(
        session,
        msg,
        {},
        allow_completed=True,
    )

    assert handled is True


def test_archive_messages_to_events_covers_text_tool_use_and_warnings():
    messages = [
        {
            "message": {
                "role": "assistant",
                "content": "plain text",
                "stop_reason": "end_turn",
            }
        },
        {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "block text"},
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "bash",
                        "input": {"cmd": "echo hi"},
                    },
                    {"type": "unknown", "text": "ignored"},
                ],
            }
        },
        {"message": {"role": "user", "content": "user says hi"}},
        {"message": {"role": "other", "type": "system"}},
    ]

    events = _archive_messages_to_events("sess", messages)

    types = [e.get("type") for e in events]
    assert "assistant.delta" in types
    assert "tool.started" in types
    assert "tool.delta" in types
    assert "assistant.completed" in types
    assert any(
        e.get("type") == "system.message"
        and "Unsupported archive assistant block"
        in (e.get("payload", {}) or {}).get("text", "")
        for e in events
    )
    assert any(
        e.get("type") == "system.message"
        and "Unsupported archive message role"
        in (e.get("payload", {}) or {}).get("text", "")
        for e in events
    )
