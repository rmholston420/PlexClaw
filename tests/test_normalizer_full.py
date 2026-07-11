from __future__ import annotations

from app.normalizer import (
    normalize_assistant_completed,
    normalize_session_failed,
    normalize_system_message,
    normalize_text_delta,
    normalize_tool_completed,
    normalize_tool_delta,
    normalize_tool_permission_decided,
    normalize_tool_started,
)
from app.schemas import PROTOCOL_VERSION, WSEnvelope


def test_normalize_system_message_defaults_to_info():
    env = normalize_system_message("s1", 1, "hello")
    assert isinstance(env, WSEnvelope)
    assert env.protocol_version == PROTOCOL_VERSION
    assert env.type == "system.message"
    assert env.payload == {"text": "hello", "level": "info"}


def test_normalize_system_message_custom_level():
    env = normalize_system_message("s1", 2, "boom", level="error")
    assert env.payload == {"text": "boom", "level": "error"}


def test_normalize_session_failed_payload():
    env = normalize_session_failed("s1", 3, "bad things")
    assert env.type == "session.failed"
    assert env.payload == {"error": "bad things"}


def test_normalize_session_failed_empty_error():
    env = normalize_session_failed("s1", 4, "")
    assert env.payload == {"error": ""}


def test_normalize_tool_permission_decided_approved():
    env = normalize_tool_permission_decided(
        "s1", 5, "t1", "bash", {"cmd": "ls"}, "approved"
    )
    assert env.type == "tool.permission_decided"
    assert env.payload == {
        "tool_id": "t1",
        "tool_name": "bash",
        "tool_input": {"cmd": "ls"},
        "decision": "approved",
    }


def test_normalize_tool_permission_decided_rejected():
    env = normalize_tool_permission_decided(
        "s1", 6, "t2", "edit", {"path": "x"}, "rejected"
    )
    assert env.payload == {
        "tool_id": "t2",
        "tool_name": "edit",
        "tool_input": {"path": "x"},
        "decision": "rejected",
    }


def test_normalize_tool_delta_defaults_optional_fields_to_none():
    env = normalize_tool_delta("s1", 7, "t3", "par")
    assert env.type == "tool.delta"
    assert env.payload == {
        "tool_id": "t3",
        "tool_name": None,
        "partial": "par",
        "tool_input": None,
    }


def test_normalize_tool_delta_with_explicit_fields():
    env = normalize_tool_delta(
        "s1", 8, "t4", "", tool_name="bash", tool_input={"cmd": "pwd"}
    )
    assert env.payload == {
        "tool_id": "t4",
        "tool_name": "bash",
        "partial": "",
        "tool_input": {"cmd": "pwd"},
    }


def test_normalize_tool_completed_default_is_error_false():
    env = normalize_tool_completed("s1", 9, "t5", "bash", {"ok": True})
    assert env.type == "tool.completed"
    assert env.payload == {
        "tool_id": "t5",
        "tool_name": "bash",
        "output": {"ok": True},
        "is_error": False,
    }


def test_normalize_tool_completed_error_true_and_none_output():
    env = normalize_tool_completed("s1", 10, "t6", "bash", None, is_error=True)
    assert env.payload == {
        "tool_id": "t6",
        "tool_name": "bash",
        "output": None,
        "is_error": True,
    }


def test_normalize_assistant_completed_usage_none_coerces_to_empty_dict():
    env = normalize_assistant_completed("s1", 11, "end_turn", None)
    assert env.type == "assistant.completed"
    assert env.payload == {"stop_reason": "end_turn", "usage": {}}


def test_normalize_assistant_completed_custom_stop_reason_and_usage():
    env = normalize_assistant_completed(
        "s1", 12, "max_tokens", {"input_tokens": 1, "output_tokens": 2}
    )
    assert env.payload == {
        "stop_reason": "max_tokens",
        "usage": {"input_tokens": 1, "output_tokens": 2},
    }


def test_normalize_text_delta_round_trip():
    env = normalize_text_delta("s1", 13, "chunk")
    assert env.type == "assistant.delta"
    assert env.payload == {"text": "chunk"}


def test_normalize_tool_started_round_trip():
    env = normalize_tool_started("s1", 14, "t7", "grep", {"pattern": "TODO"})
    assert env.type == "tool.started"
    assert env.payload == {
        "tool_id": "t7",
        "tool_name": "grep",
        "tool_input": {"pattern": "TODO"},
    }
