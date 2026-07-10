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
        "assistant.completed",
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
