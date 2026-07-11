from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.runtime_sdk as runtime_sdk
from app.schemas import SessionCreateRequest


@pytest.fixture
def clean_sessions():
    runtime_sdk._sessions.clear()
    yield
    runtime_sdk._sessions.clear()


def make_session(session_id: str = "sess-1", **kwargs):
    return runtime_sdk.LiveSession(
        id=session_id,
        model=kwargs.get("model", "claude-sonnet-4-5"),
        cwd=kwargs.get("cwd"),
        provider=kwargs.get("provider", "cloud"),
        permission_mode=kwargs.get("permission_mode", "auto"),
        resume_session_id=kwargs.get("resume_session_id"),
        fork_session=kwargs.get("fork_session", False),
        mock_mode=kwargs.get("mock_mode", True),
    )


def test_list_context_files_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        runtime_sdk.list_context_files("missing")


def test_list_context_files_returns_filename_and_size(clean_sessions):
    session = make_session()
    session.context_files["a.txt"] = "hello"
    session.context_files["b.txt"] = "π"
    runtime_sdk._sessions[session.id] = session

    result = runtime_sdk.list_context_files(session.id)

    assert result == [
        {"filename": "a.txt", "size": len(b"hello")},
        {"filename": "b.txt", "size": len("π".encode())},
    ]


def test_add_context_file_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        runtime_sdk.add_context_file("missing", "a.txt", "hello")


def test_add_context_file_enforces_max_files(clean_sessions):
    session = make_session()
    session.context_files = {f"f{i}.txt": "x" for i in range(10)}
    runtime_sdk._sessions[session.id] = session

    with pytest.raises(ValueError, match="maximum 10 context files allowed"):
        runtime_sdk.add_context_file(session.id, "new.txt", "hello")


def test_add_context_file_allows_overwrite_at_limit(clean_sessions):
    session = make_session()
    session.context_files = {f"f{i}.txt": "x" for i in range(10)}
    session._context_injected = True
    runtime_sdk._sessions[session.id] = session

    result = runtime_sdk.add_context_file(session.id, "f0.txt", "updated")

    assert result == {"filename": "f0.txt", "size": len(b"updated")}
    assert session.context_files["f0.txt"] == "updated"
    assert session._context_injected is False


def test_add_context_file_enforces_size_limit(clean_sessions):
    session = make_session()
    runtime_sdk._sessions[session.id] = session
    too_large = "x" * (200 * 1024 + 1)

    with pytest.raises(ValueError, match="file exceeds 200KB limit"):
        runtime_sdk.add_context_file(session.id, "big.txt", too_large)


def test_add_context_file_stores_content_and_resets_injection(clean_sessions):
    session = make_session()
    session._context_injected = True
    runtime_sdk._sessions[session.id] = session

    result = runtime_sdk.add_context_file(session.id, "notes.txt", "abc")

    assert result == {"filename": "notes.txt", "size": 3}
    assert session.context_files == {"notes.txt": "abc"}
    assert session._context_injected is False


def test_remove_context_file_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        runtime_sdk.remove_context_file("missing", "a.txt")


def test_remove_context_file_missing_filename_raises(clean_sessions):
    session = make_session()
    runtime_sdk._sessions[session.id] = session

    with pytest.raises(KeyError, match="context file not found: a.txt"):
        runtime_sdk.remove_context_file(session.id, "a.txt")


def test_remove_context_file_deletes_and_resets_injection(clean_sessions):
    session = make_session()
    session.context_files["a.txt"] = "hello"
    session._context_injected = True
    runtime_sdk._sessions[session.id] = session

    runtime_sdk.remove_context_file(session.id, "a.txt")

    assert session.context_files == {}
    assert session._context_injected is False


def test_inject_context_returns_prompt_when_no_files():
    session = make_session()
    assert runtime_sdk._inject_context_into_prompt(session, "hello") == "hello"


def test_inject_context_returns_prompt_when_already_injected():
    session = make_session()
    session.context_files = {"a.txt": "hello"}
    session._context_injected = True

    assert runtime_sdk._inject_context_into_prompt(session, "hello") == "hello"


def test_inject_context_includes_files_and_marks_injected():
    session = make_session()
    session.context_files = {"a.txt": "AAA", "b.txt": "BBB"}

    result = runtime_sdk._inject_context_into_prompt(session, "prompt text")

    assert "Attached file context:" in result
    assert "--- FILE: a.txt ---" in result
    assert "--- FILE: b.txt ---" in result
    assert "--- USER PROMPT ---" in result
    assert "prompt text" in result
    assert session._context_injected is True


@pytest.mark.asyncio
async def test_update_session_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime_sdk.update_session("missing", permission_mode="auto")


@pytest.mark.asyncio
async def test_update_session_invalid_permission_mode_raises(clean_sessions):
    session = make_session()
    runtime_sdk._sessions[session.id] = session

    with pytest.raises(ValueError, match="invalid permission_mode: nope"):
        await runtime_sdk.update_session(session.id, permission_mode="nope")


@pytest.mark.asyncio
async def test_update_session_updates_permission_mode(clean_sessions):
    session = make_session(permission_mode="auto")
    runtime_sdk._sessions[session.id] = session

    result = await runtime_sdk.update_session(session.id, permission_mode="manual")

    assert result is session
    assert session.permission_mode == "manual"


@pytest.mark.asyncio
async def test_create_session_missing_cwd_raises(tmp_path):
    missing = tmp_path / "does-not-exist"

    req = SessionCreateRequest(model="claude-sonnet-4-5", cwd=str(missing))

    with pytest.raises(ValueError, match="cwd does not exist:"):
        await runtime_sdk.create_session(req)


@pytest.mark.asyncio
async def test_create_session_non_directory_cwd_raises(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")

    req = SessionCreateRequest(model="claude-sonnet-4-5", cwd=str(file_path))

    with pytest.raises(ValueError, match="cwd is not a directory:"):
        await runtime_sdk.create_session(req)


@pytest.mark.asyncio
async def test_create_session_mock_mode_assigns_mock_client(
    monkeypatch, clean_sessions
):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)

    req = SessionCreateRequest(model="claude-sonnet-4-5")
    session = await runtime_sdk.create_session(req)

    assert session.mock_mode is True
    assert isinstance(session._client, runtime_sdk.MockSDKClient)
    assert emitted
    assert emitted[0].type == "system.message"
    assert emitted[0].payload["mock_mode"] is True


class ToolResultBlock:
    def __init__(self, tool_use_id=None, content=None, is_error=False):
        self.tool_use_id = tool_use_id
        self.content = content
        self.is_error = is_error


@pytest.mark.asyncio
async def test_emit_tool_completed_ignores_non_tool_blocks(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    session = make_session()
    message = SimpleNamespace(content=[{"type": "text", "text": "hello"}])
    pending = {"tool-1": {"tool_name": "bash"}}

    await runtime_sdk._emit_tool_completed_from_message(session, message, pending)

    assert emitted == []
    assert pending == {"tool-1": {"tool_name": "bash"}}


@pytest.mark.asyncio
async def test_emit_tool_completed_skips_when_no_tool_id(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    session = make_session()
    message = SimpleNamespace(content=[{"type": "tool_result", "content": "done"}])
    pending = {"tool-1": {"tool_name": "bash"}}

    await runtime_sdk._emit_tool_completed_from_message(session, message, pending)

    assert emitted == []
    assert "tool-1" in pending


@pytest.mark.asyncio
async def test_emit_tool_completed_uses_parent_tool_id(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    session = make_session()
    message = SimpleNamespace(
        parent_tool_use_id="tool-1",
        content=[{"type": "tool_result", "content": [{"type": "text", "text": "ok"}]}],
    )
    pending = {"tool-1": {"tool_name": "bash"}}

    await runtime_sdk._emit_tool_completed_from_message(session, message, pending)

    assert len(emitted) == 1
    assert emitted[0].type == "tool.completed"
    assert emitted[0].payload["tool_id"] == "tool-1"
    assert emitted[0].payload["tool_name"] == "bash"
    assert emitted[0].payload["output"] == "ok"
    assert pending == {}


@pytest.mark.asyncio
async def test_emit_tool_completed_handles_object_block_type_name(monkeypatch):
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    session = make_session()
    message = SimpleNamespace(content=[ToolResultBlock("tool-9", "done", True)])
    pending = {}

    await runtime_sdk._emit_tool_completed_from_message(session, message, pending)

    assert len(emitted) == 1
    assert emitted[0].payload["tool_id"] == "tool-9"
    assert emitted[0].payload["tool_name"] == "tool"
    assert emitted[0].payload["output"] == "done"
    assert emitted[0].payload["is_error"] is True


@pytest.mark.asyncio
async def test_submit_prompt_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime_sdk.submit_prompt("missing", "hello")


@pytest.mark.asyncio
async def test_submit_prompt_without_client_raises(clean_sessions):
    session = make_session()
    session._client = None
    runtime_sdk._sessions[session.id] = session

    with pytest.raises(RuntimeError, match="Session client is not initialized"):
        await runtime_sdk.submit_prompt(session.id, "hello")


@pytest.mark.asyncio
async def test_submit_prompt_sets_ready_after_success(monkeypatch, clean_sessions):
    emitted = []
    streamed = []

    async def fake_emit(session, env):
        emitted.append(env)

    async def fake_stream(session, prompt):
        streamed.append(prompt)

    session = make_session()
    session._client = object()
    runtime_sdk._sessions[session.id] = session

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    monkeypatch.setattr(runtime_sdk, "_stream_sdk", fake_stream)

    await runtime_sdk.submit_prompt(session.id, "hello world")

    assert session.status == "ready"
    assert streamed == ["hello world"]
    assert emitted[0].type == "system.message"
    assert "Prompt received" in emitted[0].payload["text"]


class DrainClient:
    def __init__(self, messages=None, interrupt_exc=None):
        self.messages = messages or []
        self.interrupt_exc = interrupt_exc
        self.interrupted = 0

    async def interrupt(self):
        self.interrupted += 1
        if self.interrupt_exc:
            raise self.interrupt_exc

    async def receive_response(self):
        for item in self.messages:
            yield item


@pytest.mark.asyncio
async def test_interrupt_session_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime_sdk.interrupt_session("missing")


@pytest.mark.asyncio
async def test_interrupt_session_drains_real_sdk_queue(monkeypatch, clean_sessions):
    emitted = []
    handled = []

    async def fake_emit(session, env):
        emitted.append(env)

    async def fake_handle(session, message, pending, allow_completed):
        handled.append((message, allow_completed))
        return False

    session = make_session()
    session.mock_mode = False
    session._client = DrainClient(messages=["m1", "m2"])
    runtime_sdk._sessions[session.id] = session

    monkeypatch.setattr(runtime_sdk, "_emit", fake_emit)
    monkeypatch.setattr(runtime_sdk, "_handle_sdk_terminal_message", fake_handle)

    await runtime_sdk.interrupt_session(session.id)

    assert session.status == "interrupted"
    assert session._client.interrupted == 1
    assert handled == [("m1", False), ("m2", False)]
    assert emitted[-1].type == "session.interrupted"


class CloseFailClient:
    def __init__(self, close_exc=None, interrupt_exc=None, close_returns_coro=False):
        self.close_exc = close_exc
        self.interrupt_exc = interrupt_exc
        self.close_returns_coro = close_returns_coro
        self.interrupted = 0
        self.closed = 0

    async def interrupt(self):
        self.interrupted += 1
        if self.interrupt_exc:
            raise self.interrupt_exc

    def close(self):
        self.closed += 1
        if self.close_exc:
            raise self.close_exc
        if self.close_returns_coro:
            async def _done():
                return None
            return _done()
        return None


@pytest.mark.asyncio
async def test_delete_session_missing_session_raises():
    with pytest.raises(KeyError, match="Session missing not found"):
        await runtime_sdk.delete_session("missing")


@pytest.mark.asyncio
async def test_delete_session_clears_state_and_removes_session(clean_sessions):
    session = make_session()
    session.context_files["a.txt"] = "hello"
    session.pending_approvals["tool-1"] = runtime_sdk.PendingApproval(
        tool_id="tool-1", tool_name="bash", tool_input={}
    )
    session._context_injected = True
    session._client = CloseFailClient(close_returns_coro=True)
    runtime_sdk._sessions[session.id] = session

    await runtime_sdk.delete_session(session.id)

    assert session.context_files == {}
    assert session.pending_approvals == {}
    assert session._context_injected is False
    assert session.status == "deleted"
    assert session._client is None
    assert session.id not in runtime_sdk._sessions


@pytest.mark.asyncio
async def test_delete_session_logs_close_failure(caplog, clean_sessions):
    session = make_session()
    session._client = CloseFailClient(close_exc=RuntimeError("close boom"))
    runtime_sdk._sessions[session.id] = session

    with caplog.at_level("WARNING"):
        await runtime_sdk.delete_session(session.id)

    assert "Session delete close failed: close boom" in caplog.text


def test_sdksession_to_dict_none_returns_empty_dict():
    assert runtime_sdk._sdksession_to_dict(None) == {}


def test_sdksession_to_dict_converts_object():
    info = SimpleNamespace(
        session_id="s1",
        summary="summary",
        last_modified=123,
        file_size=50,
        custom_title="title",
        first_prompt="first",
        git_branch="main",
        cwd="/tmp/repo",
        tag="green",
        created_at=77,
    )

    result = runtime_sdk._sdksession_to_dict(info)

    assert result == {
        "session_id": "s1",
        "summary": "summary",
        "last_modified": 123,
        "file_size": 50,
        "custom_title": "title",
        "first_prompt": "first",
        "git_branch": "main",
        "cwd": "/tmp/repo",
        "tag": "green",
        "created_at": 77,
    }


def test_sdkmessage_to_dict_none_returns_empty_dict():
    assert runtime_sdk._sdkmessage_to_dict(None) == {}


def test_sdkmessage_to_dict_converts_object():
    msg = SimpleNamespace(
        type="assistant",
        uuid="u1",
        session_id="s1",
        message={"role": "assistant", "content": "hi"},
        parent_tool_use_id="tool-1",
    )

    result = runtime_sdk._sdkmessage_to_dict(msg)

    assert result == {
        "type": "assistant",
        "uuid": "u1",
        "session_id": "s1",
        "message": {"role": "assistant", "content": "hi"},
        "parent_tool_use_id": "tool-1",
    }


def test_archive_messages_to_events_handles_strings_blocks_and_warnings():
    events = runtime_sdk._archive_messages_to_events(
        "sess-1",
        [
            {
                "message": {
                    "role": "assistant",
                    "content": "hello",
                    "stop_reason": "end_turn",
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "chunk"},
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "bash",
                            "input": {"cmd": "ls"},
                        },
                        {"type": "weird"},
                        "not-a-dict",
                    ],
                    "stop_reason": "end_turn",
                }
            },
            {"message": {"role": "user", "content": "ignored"}},
            {"type": "meta"},
        ],
    )

    assert [e["type"] for e in events] == [
        "assistant.delta",
        "assistant.completed",
        "assistant.delta",
        "tool.started",
        "tool.delta",
        "system.message",
        "assistant.completed",
        "system.message",
    ]
    assert events[0]["seq"] == 1
    assert events[-1]["seq"] == len(events)
    assert events[5]["payload"]["level"] == "warn"
    assert "Unsupported archive assistant block: weird" in events[5]["payload"]["text"]
    assert "Unsupported archive message role" in events[-1]["payload"]["text"]


@pytest.mark.asyncio
async def test_list_archive_sessions_returns_empty_when_sdk_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    assert await runtime_sdk.list_archive_sessions() == []


@pytest.mark.asyncio
async def test_list_archive_sessions_sorts_descending(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(
        runtime_sdk,
        "_sdk_list_sessions",
        lambda: [
            SimpleNamespace(session_id="a", last_modified=1),
            SimpleNamespace(session_id="b", last_modified=10),
        ],
    )

    result = await runtime_sdk.list_archive_sessions()

    assert [item["session_id"] for item in result] == ["b", "a"]


@pytest.mark.asyncio
async def test_list_archive_sessions_logs_and_returns_empty_on_error(
    monkeypatch, caplog
):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)

    def boom():
        raise RuntimeError("list boom")

    monkeypatch.setattr(runtime_sdk, "_sdk_list_sessions", boom)

    with caplog.at_level("WARNING"):
        result = await runtime_sdk.list_archive_sessions()

    assert result == []
    assert "list_sessions error: list boom" in caplog.text


@pytest.mark.asyncio
async def test_get_archive_session_returns_fallback_when_sdk_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    assert await runtime_sdk.get_archive_session("sess-x") == {"id": "sess-x"}


@pytest.mark.asyncio
async def test_get_archive_session_returns_converted_info(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(
        runtime_sdk,
        "_sdk_get_session_info",
        lambda session_id: SimpleNamespace(session_id=session_id, summary="summary"),
    )

    result = await runtime_sdk.get_archive_session("sess-x")

    assert result["session_id"] == "sess-x"
    assert result["summary"] == "summary"


@pytest.mark.asyncio
async def test_get_archive_session_logs_and_returns_fallback_on_error(
    monkeypatch, caplog
):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)

    def boom(session_id):
        raise RuntimeError("info boom")

    monkeypatch.setattr(runtime_sdk, "_sdk_get_session_info", boom)

    with caplog.at_level("WARNING"):
        result = await runtime_sdk.get_archive_session("sess-x")

    assert result == {"id": "sess-x"}
    assert "get_session_info error: info boom" in caplog.text


@pytest.mark.asyncio
async def test_get_archive_messages_returns_empty_when_sdk_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    assert await runtime_sdk.get_archive_messages("sess-x") == []


@pytest.mark.asyncio
async def test_get_archive_messages_converts_objects(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(
        runtime_sdk,
        "_sdk_get_session_messages",
        lambda session_id: [
            SimpleNamespace(
                type="assistant",
                uuid="u1",
                session_id=session_id,
                message={"a": 1},
            ),
        ],
    )

    result = await runtime_sdk.get_archive_messages("sess-x")

    assert result == [
        {
            "type": "assistant",
            "uuid": "u1",
            "session_id": "sess-x",
            "message": {"a": 1},
            "parent_tool_use_id": None,
        }
    ]


@pytest.mark.asyncio
async def test_get_archive_messages_logs_and_returns_empty_on_error(
    monkeypatch, caplog
):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)

    def boom(session_id):
        raise RuntimeError("messages boom")

    monkeypatch.setattr(runtime_sdk, "_sdk_get_session_messages", boom)

    with caplog.at_level("WARNING"):
        result = await runtime_sdk.get_archive_messages("sess-x")

    assert result == []
    assert "get_session_messages error: messages boom" in caplog.text


@pytest.mark.asyncio
async def test_get_archive_replay_events_uses_archive_messages(monkeypatch):
    async def fake_get_archive_messages(session_id):
        return [
            {
                "message": {
                    "role": "assistant",
                    "content": "hello",
                    "stop_reason": "end_turn",
                }
            }
        ]

    monkeypatch.setattr(runtime_sdk, "get_archive_messages", fake_get_archive_messages)

    result = await runtime_sdk.get_archive_replay_events("sess-x")

    assert [item["type"] for item in result] == [
        "assistant.delta",
        "assistant.completed",
    ]


@pytest.mark.asyncio
async def test_rename_archive_session_noops_when_sdk_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    await runtime_sdk.rename_archive_session("sess-x", "New title")


@pytest.mark.asyncio
async def test_rename_archive_session_logs_warning_on_error(monkeypatch, caplog):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)

    def boom(session_id, title):
        raise RuntimeError("rename boom")

    monkeypatch.setattr(runtime_sdk, "_sdk_rename_session", boom)

    with caplog.at_level("WARNING"):
        await runtime_sdk.rename_archive_session("sess-x", "New title")

    assert "rename_session error: rename boom" in caplog.text


@pytest.mark.asyncio
async def test_tag_archive_session_noops_when_sdk_unavailable(monkeypatch):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", False)
    await runtime_sdk.tag_archive_session("sess-x", "green")


@pytest.mark.asyncio
async def test_tag_archive_session_logs_warning_on_error(monkeypatch, caplog):
    monkeypatch.setattr(runtime_sdk, "_SDK_AVAILABLE", True)

    def boom(session_id, tag):
        raise RuntimeError("tag boom")

    monkeypatch.setattr(runtime_sdk, "_sdk_tag_session", boom)

    with caplog.at_level("WARNING"):
        await runtime_sdk.tag_archive_session("sess-x", "green")

    assert "tag_session error: tag boom" in caplog.text

# --- remaining runtime_sdk branch coverage ---

def test_archive_messages_to_events_uses_dict_for_mapping_like_env(monkeypatch):
    import app.runtime_sdk as runtime_sdk

    original_text = runtime_sdk.normalize_text_delta
    original_completed = runtime_sdk.normalize_assistant_completed

    class MappingEnvelope:
        def __init__(self, data):
            self._data = data

        def __iter__(self):
            return iter(self._data.items())

    def fake_text_delta(session_id, seq, text):
        return MappingEnvelope(
            {
                "type": "assistant.delta",
                "session_id": session_id,
                "seq": seq,
                "payload": {"text": text},
            }
        )

    def fake_completed(session_id, seq, stop_reason, usage=None):
        return MappingEnvelope(
            {
                "type": "assistant.completed",
                "session_id": session_id,
                "seq": seq,
                "payload": {"stop_reason": stop_reason, "usage": usage},
            }
        )

    monkeypatch.setattr(runtime_sdk, "normalize_text_delta", fake_text_delta)
    monkeypatch.setattr(runtime_sdk, "normalize_assistant_completed", fake_completed)

    messages = [
        {
            "message": {
                "role": "assistant",
                "content": "hello from mapping env",
                "stop_reason": "end_turn",
            }
        }
    ]

    events = runtime_sdk._archive_messages_to_events("sess-map", messages)

    assert [event["type"] for event in events] == [
        "assistant.delta",
        "assistant.completed",
    ]
    assert events[0]["payload"]["text"] == "hello from mapping env"
    assert events[0]["seq"] == 1
    assert events[1]["seq"] == 2

    monkeypatch.setattr(runtime_sdk, "normalize_text_delta", original_text)
    monkeypatch.setattr(
        runtime_sdk,
        "normalize_assistant_completed",
        original_completed,
    )
