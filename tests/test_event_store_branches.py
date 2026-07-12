from __future__ import annotations

import json
import sqlite3

import pytest

import app.event_store as es
from app.event_store import append_event, search_events

_INSERT_SQL = (
    "INSERT INTO events "
    "(session_id, seq, type, payload, created_at) "
    "VALUES (?,?,?,?,datetime('now'))"
)


@pytest.fixture(autouse=True)
def _fresh_event_store_db(tmp_path, monkeypatch):
    conn = getattr(es, "_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    monkeypatch.setattr(es, "DB_PATH", tmp_path / "events_branches.db")
    monkeypatch.setattr(es, "_conn", None)
    monkeypatch.setattr(es, "_conn_path", None)
    monkeypatch.setattr(es, "_fts_available", None)
    monkeypatch.setattr(es, "_db_initialized", False)
    yield
    conn = getattr(es, "_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def test_get_conn_closes_old_connection_when_db_path_changes(monkeypatch, tmp_path):
    old_db = tmp_path / "old.db"
    new_db = tmp_path / "new.db"

    class ClosingConn:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    old_conn = ClosingConn()
    monkeypatch.setattr(es, "_conn", old_conn)
    monkeypatch.setattr(es, "_conn_path", old_db)
    monkeypatch.setattr(es, "DB_PATH", new_db)

    conn = es._get_conn()

    assert old_conn.closed is True
    assert conn is not None
    assert es._conn_path == new_db


def test_get_conn_ignores_close_errors_when_replacing_connection(
    monkeypatch, tmp_path
):
    old_db = tmp_path / "old.db"
    new_db = tmp_path / "new.db"

    class BadCloseConn:
        def close(self):
            raise RuntimeError("close failed")

    monkeypatch.setattr(es, "_conn", BadCloseConn())
    monkeypatch.setattr(es, "_conn_path", old_db)
    monkeypatch.setattr(es, "DB_PATH", new_db)

    conn = es._get_conn()

    assert conn is not None
    assert es._conn_path == new_db


def test_check_fts5_available_locked_sets_false_on_operational_error(
    monkeypatch, caplog
):
    monkeypatch.setattr(es, "_fts_available", None)

    class FailingConn:
        def execute(self, sql):
            raise sqlite3.OperationalError("fts unavailable")

    monkeypatch.setattr(es, "_get_conn", lambda: FailingConn())

    with caplog.at_level("WARNING"):
        out = es._check_fts5_available_locked()

    assert out is False
    assert es._fts_available is False


def test_check_fts5_returns_cached_value_without_lock_path(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", True)

    def boom():
        raise AssertionError("should not enter locked checker")

    monkeypatch.setattr(es, "_check_fts5_available_locked", boom)

    assert es._check_fts5() is True


def test_check_fts5_uses_lock_path_when_cache_unknown(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", None)
    monkeypatch.setattr(es, "_check_fts5_available_locked", lambda: False)

    assert es._check_fts5() is False


def test_init_db_backfills_fts_from_existing_events_skipping_empty_bodies(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", True)
    conn = es._get_conn()

    conn.execute(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        _INSERT_SQL,
        ("s1", 1, "assistant.delta", json.dumps({"text": "find me"})),
    )
    conn.execute(
        _INSERT_SQL,
        ("s1", 2, "unknown.event", json.dumps({"x": 1})),
    )
    conn.commit()

    monkeypatch.setattr(es, "_db_initialized", False)
    es.init_db()

    rows = conn.execute(
        "SELECT role, body, session_id, seq FROM events_fts ORDER BY seq ASC"
    ).fetchall()

    assert len(rows) == 1
    assert rows[0]["role"] == "assistant"
    assert rows[0]["body"] == "find me"
    assert rows[0]["session_id"] == "s1"
    assert rows[0]["seq"] == 1


async def test_search_events_uses_linear_branch_when_fts_unavailable(monkeypatch):
    await append_event("s1", 1, "assistant.delta", {"text": "linear only"})

    monkeypatch.setattr(es, "_fts_available", False)

    called = {"linear": False}

    def fake_linear(conn, needle):
        called["linear"] = True
        return [{"session_id": "s1", "message_id": 1}]

    monkeypatch.setattr(es, "_search_linear", fake_linear)

    hits = es._blocking_search("linear only")

    assert called["linear"] is True
    assert hits == [{"session_id": "s1", "message_id": 1}]


def test_search_fts5_falls_back_to_linear_on_operational_error(monkeypatch, caplog):
    class FailingConn:
        def execute(self, sql, params=()):
            raise sqlite3.OperationalError("fts query broke")

    monkeypatch.setattr(
        es,
        "_search_linear",
        lambda conn, query: [{"session_id": "fallback", "message_id": 99}],
    )

    with caplog.at_level("WARNING"):
        hits = es._search_fts5(FailingConn(), "fallback needle")

    assert hits == [{"session_id": "fallback", "message_id": 99}]
    assert "falling back to linear" in caplog.text


async def test_search_linear_skips_events_without_searchable_body(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", False)
    await append_event("s1", 1, "unknown.event", {"x": "y"})

    hits = es._blocking_search("y")
    assert hits == []


async def test_search_linear_returns_empty_when_query_not_found(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", False)
    await append_event("s1", 1, "assistant.delta", {"text": "no match here"})

    hits = es._blocking_search("needle")
    assert hits == []


def test_search_linear_deduplicates_duplicate_session_and_seq(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", False)
    conn = es._get_conn()
    es.init_db()

    payload = json.dumps({"text": "duplicate needle"})
    conn.execute(_INSERT_SQL, ("dup", 7, "assistant.delta", payload))
    conn.execute(_INSERT_SQL, ("dup", 7, "assistant.delta", payload))
    conn.commit()

    hits = es._blocking_search("duplicate needle")

    assert len(hits) == 1
    assert hits[0]["session_id"] == "dup"
    assert hits[0]["message_id"] == 7


def test_search_linear_normalizes_newlines_in_snippet(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", False)
    es._blocking_append("s1", 1, "assistant.delta", {"text": "alpha\nneedle\nomega"}, '{"text": "alpha\\nneedle\\nomega"}')

    hits = es._blocking_search("needle")

    assert len(hits) == 1
    assert "\n" not in hits[0]["snippet"]
    assert "needle" in hits[0]["snippet"]


def test_search_linear_limits_results_to_200(monkeypatch):
    monkeypatch.setattr(es, "_fts_available", False)

    for i in range(205):
        es._blocking_append(f"s{i:03d}", i, "assistant.delta", {"text": "cap needle"}, '{"text": "cap needle"}')

    hits = es._blocking_search("cap needle")

    assert len(hits) == 200
