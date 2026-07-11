"""Full contract tests for every function in app/normalizer.py.

Covers every public normalizer function including the previously
untested normalize_system_message, normalize_session_failed,
normalize_tool_permission_decided, and normalize_tool_delta
with optional keyword arguments.
"""
from __future__ import annotations

import pytest

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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_envelope(env: WSEnvelope, expected_type: str, session_id: str, seq: int):
    assert isinstance(env, WSEnvelope)
    assert env.type == expected_type
    assert env.session_id == session_id
    assert env.seq == seq
    assert env.protocol_version == PROTOCOL_VERSION


# ---------------------------------------------------------------------------
# normalize_text_delta
# ---------------------------------------------------------------------------

def test_normalize_text_delta_type_and_payload():
    env = normalize_text_delta("s1", 0, "hello world")
    _assert_envelope(env, "assistant.delta", "s1", 0)
    assert env.payload == {"text": "hello world"}


def test_normalize_text_delta_empty_string():
    env = normalize_text_delta("s2", 5, "")
    assert env.payload["text"] == ""


# ---------------------------------------------------------------------------
# normalize_tool_started
# ---------------------------------------------------------------------------

def test_normalize_tool_started_full_payload():
    env = normalize_tool_started("sess", 1, "tid1", "bash", {"cmd": "ls -la"})
    _assert_envelope(env, "tool.started", "sess", 1)
    assert env.payload["tool_id"] == "tid1"
    assert env.payload["tool_name"] == "bash"
    assert env.payload["tool_input"] == {"cmd": "ls -la"}


def test_normalize_tool_started_none_input():
    env = normalize_tool_started("s", 2, "t2", "computer", None)
    assert env.payload["tool_input"] is None


# ---------------------------------------------------------------------------
# normalize_tool_delta
# ---------------------------------------------------------------------------

def test_normalize_tool_delta_minimal():
    env = normalize_tool_delta("s", 3, "t3", "partial-text")
    _assert_envelope(env, "tool.delta", "s", 3)
    assert env.payload["tool_id"] == "t3"
    assert env.payload["partial"] == "partial-text"
    assert env.payload["tool_name"] is None
    assert env.payload["tool_input"] is None


def test_normalize_tool_delta_with_optional_kwargs():
    env = normalize_tool_delta(
        "s", 4, "t4", "chunk",
        tool_name="read_file",
        tool_input={"path": "/foo"},
    )
    assert env.payload["tool_name"] == "read_file"
    assert env.payload["tool_input"] == {"path": "/foo"}


# ---------------------------------------------------------------------------
# normalize_tool_completed
# ---------------------------------------------------------------------------

def test_normalize_tool_completed_success():
    env = normalize_tool_completed("s", 5, "t5", "bash", "stdout: ok")
    _assert_envelope(env, "tool.completed", "s", 5)
    assert env.payload["output"] == "stdout: ok"
    assert env.payload["is_error"] is False


def test_normalize_tool_completed_error_flag():
    env = normalize_tool_completed("s", 6, "t6", "bash", "error msg", is_error=True)
    assert env.payload["is_error"] is True
    assert env.payload["output"] == "error msg"


def test_normalize_tool_completed_none_output():
    env = normalize_tool_completed("s", 7, "t7", "computer", None)
    assert env.payload["output"] is None


# ---------------------------------------------------------------------------
# normalize_tool_permission_decided
# ---------------------------------------------------------------------------

def test_normalize_tool_permission_decided_approved():
    env = normalize_tool_permission_decided(
        "s", 8, "t8", "bash", {"cmd": "rm -rf /"}, "approved"
    )
    _assert_envelope(env, "tool.permission_decided", "s", 8)
    assert env.payload["tool_id"] == "t8"
    assert env.payload["tool_name"] == "bash"
    assert env.payload["tool_input"] == {"cmd": "rm -rf /"}
    assert env.payload["decision"] == "approved"


def test_normalize_tool_permission_decided_rejected():
    env = normalize_tool_permission_decided(
        "s", 9, "t9", "bash", {}, "rejected"
    )
    assert env.payload["decision"] == "rejected"


# ---------------------------------------------------------------------------
# normalize_assistant_completed
# ---------------------------------------------------------------------------

def test_normalize_assistant_completed_defaults():
    env = normalize_assistant_completed("s", 10)
    _assert_envelope(env, "assistant.completed", "s", 10)
    assert env.payload["stop_reason"] == "end_turn"
    assert env.payload["usage"] == {}


def test_normalize_assistant_completed_custom_stop_reason():
    env = normalize_assistant_completed("s", 11, stop_reason="max_tokens")
    assert env.payload["stop_reason"] == "max_tokens"


def test_normalize_assistant_completed_usage_dict():
    usage = {"input_tokens": 100, "output_tokens": 50}
    env = normalize_assistant_completed("s", 12, usage=usage)
    assert env.payload["usage"] == usage


def test_normalize_assistant_completed_none_usage_becomes_empty():
    env = normalize_assistant_completed("s", 13, usage=None)
    assert env.payload["usage"] == {}


# ---------------------------------------------------------------------------
# normalize_session_failed
# ---------------------------------------------------------------------------

def test_normalize_session_failed_type_and_payload():
    env = normalize_session_failed("s", 14, "connection timeout")
    _assert_envelope(env, "session.failed", "s", 14)
    assert env.payload == {"error": "connection timeout"}


def test_normalize_session_failed_empty_error():
    env = normalize_session_failed("s", 15, "")
    assert env.payload["error"] == ""


# ---------------------------------------------------------------------------
# normalize_system_message
# ---------------------------------------------------------------------------

def test_normalize_system_message_default_level():
    env = normalize_system_message("s", 16, "Reaping idle session")
    _assert_envelope(env, "system.message", "s", 16)
    assert env.payload["text"] == "Reaping idle session"
    assert env.payload["level"] == "info"


def test_normalize_system_message_custom_level():
    env = normalize_system_message("s", 17, "Disk full", level="error")
    assert env.payload["level"] == "error"
    assert env.payload["text"] == "Disk full"


def test_normalize_system_message_warning_level():
    env = normalize_system_message("s", 18, "Slow response", level="warning")
    assert env.payload["level"] == "warning"


# ---------------------------------------------------------------------------
# Sequence monotonicity sanity check
# ---------------------------------------------------------------------------

def test_seq_values_are_stored_exactly():
    """seq is pass-through — whatever the caller provides is preserved."""
    for seq_val in (0, 1, 99, 10_000):
        env = normalize_text_delta("s", seq_val, "x")
        assert env.seq == seq_val
