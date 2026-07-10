from pathlib import Path

import app.event_store as es
from app.event_store import append_event, init_db, query_events, search_events


def _reset_conn(path: Path, monkeypatch):
    """Point event_store at a fresh temp DB and force connection re-open."""
    monkeypatch.setattr(es, "DB_PATH", path)
    monkeypatch.setattr(es, "_conn", None)
    monkeypatch.setattr(es, "_conn_path", None)
    monkeypatch.setattr(es, "_fts_available", None)


def test_event_store_append_and_query(tmp_path, monkeypatch):
    _reset_conn(tmp_path / "events.db", monkeypatch)
    init_db()
    append_event("s1", 1, "assistant.delta", {"text": "hello"})
    append_event("s1", 2, "assistant.completed", {"stop_reason": "end_turn"})

    rows = query_events("s1")
    assert len(rows) == 2
    assert rows[0]["payload"]["text"] == "hello"


def test_event_store_filters(tmp_path, monkeypatch):
    _reset_conn(tmp_path / "events.db", monkeypatch)
    init_db()
    append_event("s1", 1, "assistant.delta", {"text": "a"})
    append_event("s1", 2, "tool.started", {"tool_id": "1"})
    append_event("s1", 3, "assistant.delta", {"text": "b"})

    rows = query_events("s1", event_type="assistant.delta", since_seq=1)
    assert len(rows) == 1
    assert rows[0]["seq"] == 3


def test_search_events_returns_match(tmp_path, monkeypatch):
    _reset_conn(tmp_path / "events.db", monkeypatch)
    init_db()
    append_event("s2", 1, "assistant.delta", {"text": "The answer is forty-two"})
    append_event("s2", 2, "system.message", {"text": "session ready"})

    hits = search_events("forty-two")
    assert len(hits) >= 1
    assert hits[0]["session_id"] == "s2"


def test_search_events_no_match(tmp_path, monkeypatch):
    _reset_conn(tmp_path / "events.db", monkeypatch)
    init_db()
    append_event("s3", 1, "assistant.delta", {"text": "nothing relevant here"})

    hits = search_events("xyzzy_not_present")
    assert hits == []


def test_search_events_empty_query(tmp_path, monkeypatch):
    _reset_conn(tmp_path / "events.db", monkeypatch)
    init_db()
    append_event("s4", 1, "assistant.delta", {"text": "some text"})

    hits = search_events("  ")
    assert hits == []
