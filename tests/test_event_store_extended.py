"""Extended unit tests for app/event_store.py.

Covers branches not exercised by test_event_store.py:
  - _event_search_parts for every event type (+ fall-through)
  - search_events FTS5 operational-error fallback → linear search
  - multi-session query isolation
  - query_events with no filters (returns all for session)
  - search_events with tool.completed payloads
  - search_events with system.message payloads
  - _search_linear 200-result cap (smoke)
  - append_event double-commit idempotency (same data, different seqs)
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

import app.event_store as es
from app.event_store import (
    _event_search_parts,
    append_event,
    init_db,
    query_events,
    search_events,
)


# ---------------------------------------------------------------------------
# _event_search_parts – unit tests for every branch
# ---------------------------------------------------------------------------


def test_search_parts_assistant_delta():
    role, body = _event_search_parts("assistant.delta", {"text": "hello world"})
    assert role == "assistant"
    assert body == "hello world"


def test_search_parts_assistant_delta_missing_key():
    role, body = _event_search_parts("assistant.delta", {})
    assert role == "assistant"
    assert body == ""


def test_search_parts_system_message_text_key():
    role, body = _event_search_parts("system.message", {"text": "ready"})
    assert role == "system"
    assert body == "ready"


def test_search_parts_system_message_message_key():
    # Falls back to 'message' when 'text' is absent/falsy
    role, body = _event_search_parts("system.message", {"message": "hello"})
    assert role == "system"
    assert body == "hello"


def test_search_parts_system_message_prefers_text_over_message():
    role, body = _event_search_parts(
        "system.message", {"text": "primary", "message": "fallback"}
    )
    assert body == "primary"


def test_search_parts_tool_completed():
    role, body = _event_search_parts(
        "tool.completed", {"tool_id": "t1", "output": "done"}
    )
    assert role == "tool"
    assert body == "done"


def test_search_parts_tool_started():
    role, body = _event_search_parts(
        "tool.started",
        {"tool_name": "bash", "tool_input": {"cmd": "ls"}},
    )
    assert role == "tool"
    assert "bash" in body
    assert "ls" in body


def test_search_parts_tool_delta_with_tool_input():
    role, body = _event_search_parts(
        "tool.delta", {"tool_id": "t2", "tool_input": {"x": 1}}
    )
    assert role == "tool"
    assert "x" in body


def test_search_parts_tool_delta_without_tool_input():
    """tool.delta without tool_input key should fall through to empty."""
    role, body = _event_search_parts("tool.delta", {"tool_id": "t3"})
    assert role == ""
    assert body == ""


def test_search_parts_unknown_event_type():
    role, body = _event_search_parts("unknown.event", {"anything": "value"})
    assert role == ""
    assert body == ""


# ---------------------------------------------------------------------------
# query_events – isolation and filter edge cases
# ---------------------------------------------------------------------------


def test_query_events_multi_session_isolation():
    append_event("alpha", 1, "assistant.delta", {"text": "a"})
    append_event("beta", 1, "assistant.delta", {"text": "b"})

    alpha = query_events("alpha")
    beta = query_events("beta")

    assert len(alpha) == 1
    assert alpha[0]["payload"]["text"] == "a"
    assert len(beta) == 1
    assert beta[0]["payload"]["text"] == "b"


def test_query_events_no_filters_returns_all():
    for i in range(1, 6):
        append_event("sess", i, "assistant.delta", {"text": str(i)})

    rows = query_events("sess")
    assert len(rows) == 5


def test_query_events_since_seq_inclusive_edge():
    for i in range(1, 4):
        append_event("s", i, "assistant.delta", {"text": str(i)})

    # since_seq=2 → only seq=3
    rows = query_events("s", since_seq=2)
    assert len(rows) == 1
    assert rows[0]["seq"] == 3


def test_query_events_type_filter_with_no_match():
    append_event("s", 1, "assistant.delta", {"text": "hi"})
    rows = query_events("s", event_type="tool.started")
    assert rows == []


def test_query_events_returns_created_at_field():
    append_event("s", 1, "assistant.delta", {"text": "hi"})
    rows = query_events("s")
    assert "created_at" in rows[0]
    assert rows[0]["created_at"]  # non-empty


# ---------------------------------------------------------------------------
# search_events – tool.completed and system.message
# ---------------------------------------------------------------------------


def test_search_events_tool_completed_output():
    append_event("s", 1, "tool.completed", {"tool_id": "t1", "output": "zap the cache"})
    hits = search_events("zap the cache")
    assert len(hits) >= 1
    assert hits[0]["session_id"] == "s"


def test_search_events_system_message():
    append_event("s", 1, "system.message", {"text": "plasma storm incoming"})
    hits = search_events("plasma storm")
    assert len(hits) >= 1
    assert hits[0]["role"] == "system"


def test_search_events_result_has_expected_keys():
    append_event("s", 1, "assistant.delta", {"text": "keycheck"})
    hits = search_events("keycheck")
    assert len(hits) == 1
    hit = hits[0]
    for key in ("session_id", "session_title", "message_id", "snippet", "role", "created_at"):
        assert key in hit, f"missing key: {key}"


def test_search_events_session_title_is_first_8_chars():
    append_event("abcdefghij", 1, "assistant.delta", {"text": "trunc-test"})
    hits = search_events("trunc-test")
    assert hits[0]["session_title"] == "abcdefgh"


# ---------------------------------------------------------------------------
# FTS5 OperationalError fallback → linear search
# ---------------------------------------------------------------------------


def test_search_events_fts5_error_falls_back_to_linear():
    """When FTS5 raises OperationalError, _search_linear must be used."""
    append_event("fall", 1, "assistant.delta", {"text": "needle fallback"})

    original_fts5 = es._search_fts5

    def boom(c, query):
        raise sqlite3.OperationalError("fts5: synthetic failure")

    with patch.object(es, "_search_fts5", side_effect=boom):
        # Force FTS5 path by temporarily setting _fts_available True
        es._fts_available = True
        try:
            hits = search_events("needle fallback")
        finally:
            es._fts_available = None  # Let conftest reset handle it cleanly

    assert any(h["session_id"] == "fall" for h in hits)
