from __future__ import annotations

from app import runtime_sdk


def test_archive_replay_emits_tool_completed_for_tool_result() -> None:
    session_id = "archive-session"
    messages = [
        {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Read",
                        "input": {"file_path": "README.md"},
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-1",
                        "content": [{"type": "text", "text": "hello"}],
                        "is_error": False,
                    },
                ],
                "stop_reason": "end_turn",
            }
        }
    ]

    events = runtime_sdk._archive_messages_to_events(session_id, messages)
    event_types = [event["type"] for event in events]

    assert "tool.started" in event_types
    assert "tool.completed" in event_types

    completed = next(event for event in events if event["type"] == "tool.completed")
    payload = completed["payload"]
    assert payload["tool_id"] == "tool-1"
    assert payload["tool_name"] == "Read"
    assert payload["output"] == "hello"
    assert payload["is_error"] is False
