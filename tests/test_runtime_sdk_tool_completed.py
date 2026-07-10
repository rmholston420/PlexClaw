from __future__ import annotations

import pytest

from app.runtime_sdk import _emit_tool_completed_from_message


class DummySession:
    def __init__(self) -> None:
        self.id = "s1"
        self.seq = 0

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


class DummyBlock:
    def __init__(self, tool_use_id: str, content, is_error: bool = False) -> None:
        self.tool_use_id = tool_use_id
        self.content = content
        self.is_error = is_error


class ToolResultBlock(DummyBlock):
    pass


class DummyAssistantMessage:
    def __init__(self, content, parent_tool_use_id=None) -> None:
        self.content = content
        self.parent_tool_use_id = parent_tool_use_id


@pytest.mark.asyncio
async def test_emit_tool_completed_from_tool_result_block(monkeypatch) -> None:
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr("app.runtime_sdk._emit", fake_emit)

    session = DummySession()
    pending_tools = {
        "tool-1": {
            "tool_name": "bash",
            "tool_input": {"cmd": "pwd"},
        }
    }
    message = DummyAssistantMessage(
        [ToolResultBlock("tool-1", [{"type": "text", "text": "ok"}], False)]
    )

    await _emit_tool_completed_from_message(session, message, pending_tools)

    assert len(emitted) == 1
    evt = emitted[0]
    assert evt.type == "tool.completed"
    assert evt.payload["tool_id"] == "tool-1"
    assert evt.payload["tool_name"] == "bash"
    assert evt.payload["output"] == "ok"
    assert evt.payload["is_error"] is False
    assert pending_tools == {}


@pytest.mark.asyncio
async def test_emit_tool_completed_from_dict_style_block(monkeypatch) -> None:
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr("app.runtime_sdk._emit", fake_emit)

    session = DummySession()
    pending_tools = {"tool-2": {"tool_name": "read"}}
    message = DummyAssistantMessage(
        [{"type": "tool_result", "tool_use_id": "tool-2", "content": "file text", "is_error": False}]
    )

    await _emit_tool_completed_from_message(session, message, pending_tools)

    assert len(emitted) == 1
    evt = emitted[0]
    assert evt.type == "tool.completed"
    assert evt.payload["tool_id"] == "tool-2"
    assert evt.payload["tool_name"] == "read"
    assert evt.payload["output"] == "file text"
    assert evt.payload["is_error"] is False
    assert pending_tools == {}


@pytest.mark.asyncio
async def test_emit_tool_completed_uses_parent_tool_id_fallback(monkeypatch) -> None:
    emitted = []

    async def fake_emit(session, env):
        emitted.append(env)

    monkeypatch.setattr("app.runtime_sdk._emit", fake_emit)

    session = DummySession()
    pending_tools = {"tool-3": {"tool_name": "search"}}
    message = DummyAssistantMessage(
        [{"type": "tool_result", "content": [{"type": "text", "text": "done"}], "is_error": True}],
        parent_tool_use_id="tool-3",
    )

    await _emit_tool_completed_from_message(session, message, pending_tools)

    assert len(emitted) == 1
    evt = emitted[0]
    assert evt.payload["tool_id"] == "tool-3"
    assert evt.payload["tool_name"] == "search"
    assert evt.payload["output"] == "done"
    assert evt.payload["is_error"] is True
    assert pending_tools == {}
