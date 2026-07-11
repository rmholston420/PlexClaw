from app.main import _render_session_markdown
from app.runtime_sdk import _archive_messages_to_events


def test_archive_replay_normalizes_assistant_tool_use():
    messages = [
        {
            "type": "assistant",
            "uuid": "m1",
            "session_id": "s1",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Write",
                        "input": {"file_path": "/tmp/x.txt"},
                    }
                ],
                "stop_reason": "tool_use",
            },
            "parent_tool_use_id": None,
        }
    ]

    events = _archive_messages_to_events("s1", messages)

    assert [evt["type"] for evt in events] == [
        "tool.started",
        "tool.delta",
    ]
    assert events[1]["payload"]["tool_input"] == {"file_path": "/tmp/x.txt"}


def test_archive_replay_normalizes_assistant_text():
    messages = [
        {
            "type": "assistant",
            "uuid": "m2",
            "session_id": "s1",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "hello world"}],
                "stop_reason": "end_turn",
            },
            "parent_tool_use_id": None,
        }
    ]

    events = _archive_messages_to_events("s1", messages)

    assert [evt["type"] for evt in events] == [
        "assistant.delta",
        "assistant.completed",
    ]
    assert events[0]["payload"]["text"] == "hello world"



def test_archive_replay_tool_use_events_export_with_finalized_input():
    messages = [
        {
            "type": "assistant",
            "uuid": "m3",
            "session_id": "s1",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-7",
                        "name": "bash",
                        "input": {"cmd": "ls -la"},
                    }
                ],
                "stop_reason": "tool_use",
            },
            "parent_tool_use_id": None,
        }
    ]

    events = _archive_messages_to_events("s1", messages)
    md = _render_session_markdown("s1", events)

    assert [evt["type"] for evt in events] == [
        "tool.started",
        "tool.delta",
    ]
    assert events[1]["payload"]["tool_input"] == {"cmd": "ls -la"}
    assert "## Tool: bash" in md
    assert '"cmd": "ls -la"' in md


def test_render_session_markdown_includes_tool_permission_required_event():
    events = [
        {
            "type": "tool.permission_required",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
                "tool_input": {"cmd": "pwd"},
            },
        }
    ]

    md = _render_session_markdown("s1", events)

    assert "bash" in md
    assert "tool approval required" in md.lower()


def test_render_session_markdown_includes_tool_permission_decision_event():
    events = [
        {
            "type": "tool.permission_decided",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
                "decision": "reject",
            },
        }
    ]

    md = _render_session_markdown("s1", events)

    assert "bash" in md
    assert "reject" in md.lower()


def test_archive_replay_permission_events_can_coexist_with_tool_events():
    events = [
        {
            "type": "tool.started",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
            },
        },
        {
            "type": "tool.permission_required",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
                "tool_input": {"cmd": "pwd"},
            },
        },
        {
            "type": "tool.permission_decided",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
                "decision": "approve",
            },
        },
        {
            "type": "tool.completed",
            "payload": {
                "tool_id": "tool-1",
                "tool_name": "bash",
                "output": "/tmp",
                "is_error": False,
            },
        },
    ]

    md = _render_session_markdown("s1", events)

    assert "## Tool: bash" in md
    assert "approve" in md.lower()
    assert "/tmp" in md

def test_archive_replay_tool_events_use_monotonic_seq_numbers() -> None:
    messages = [
        {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "bash",
                        "input": {"cmd": "ls"},
                    },
                    {
                        "type": "text",
                        "text": "done",
                    },
                ],
                "stop_reason": "end_turn",
            }
        }
    ]

    events = _archive_messages_to_events("s1", messages)

    assert [event["type"] for event in events] == [
        "tool.started",
        "tool.delta",
        "assistant.delta",
        "assistant.completed",
    ]
    assert [event["seq"] for event in events] == [1, 2, 3, 4]
    assert events[0]["payload"]["tool_id"] == "tool-1"
    assert events[0]["payload"]["tool_name"] == "bash"
    assert events[1]["payload"]["tool_id"] == "tool-1"
    assert events[1]["payload"]["tool_input"] == {"cmd": "ls"}
    assert events[2]["payload"]["text"] == "done"
    assert events[3]["payload"]["stop_reason"] == "end_turn"

