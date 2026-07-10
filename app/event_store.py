"""Append-only SQLite event store for replay and audit."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

log = logging.getLogger(__name__)

DB_PATH = Path("plexclaw_events.db")

_conn: sqlite3.Connection | None = None
_conn_path: Path | None = None
_db_lock = Lock()
_fts_available: bool | None = None
_db_initialized = False


def _get_conn() -> sqlite3.Connection:
    global _conn, _conn_path
    if _conn is None or _conn_path != DB_PATH:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA cache_size=-32768")
        c.execute("PRAGMA synchronous=NORMAL")
        _conn = c
        _conn_path = DB_PATH
    return _conn


def _check_fts5() -> bool:
    global _fts_available
    if _fts_available is not None:
        return _fts_available
    try:
        c = _get_conn()
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
        c.execute("DROP TABLE IF EXISTS _fts5_probe")
        _fts_available = True
    except sqlite3.OperationalError:
        _fts_available = False
        log.warning("SQLite FTS5 unavailable – falling back to linear search")
    return _fts_available


def init_db() -> None:
    global _db_initialized
    with _db_lock:
        c = _get_conn()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                seq         INTEGER NOT NULL,
                type        TEXT    NOT NULL,
                payload     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_seq ON events (session_id, seq)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_desc "
            "ON events (created_at DESC, id DESC)"
        )

        if _check_fts5():
            c.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
                USING fts5(
                    role,
                    body,
                    session_id UNINDEXED,
                    seq UNINDEXED,
                    created_at UNINDEXED
                )
                """
            )

            (existing,) = c.execute("SELECT COUNT(*) FROM events_fts").fetchone()
            if existing == 0:
                rows = c.execute(
                    "SELECT session_id, seq, type, payload, created_at "
                    "FROM events ORDER BY id ASC"
                ).fetchall()
                for r in rows:
                    payload = json.loads(r["payload"])
                    role, body = _event_search_parts(r["type"], payload)
                    if not body:
                        continue
                    c.execute(
                        (
                            "INSERT INTO events_fts("
                            "role, body, session_id, seq, created_at"
                            ") VALUES (?,?,?,?,?)"
                        ),
                        (role, body, r["session_id"], r["seq"], r["created_at"]),
                    )

        c.commit()
        _db_initialized = True


def _ensure_initialized() -> None:
    if _db_initialized:
        return
    init_db()


def append_event(
    session_id: str,
    seq: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    _ensure_initialized()
    payload_json = json.dumps(payload)
    with _db_lock:
        c = _get_conn()
        c.execute(
            "INSERT INTO events (session_id, seq, type, payload) VALUES (?,?,?,?)",
            (session_id, seq, event_type, payload_json),
        )

        if _check_fts5():
            role, body = _event_search_parts(event_type, payload)
            if body:
                c.execute(
                    "INSERT INTO events_fts(role, body, session_id, seq, created_at) "
                    "VALUES (?,?,?,?,datetime('now'))",
                    (role, body, session_id, seq),
                )

        c.commit()


def query_events(
    session_id: str,
    event_type: str | None = None,
    since_seq: int | None = None,
) -> list[dict[str, Any]]:
    _ensure_initialized()
    sql = "SELECT * FROM events WHERE session_id = ?"
    params: list[Any] = [session_id]
    if event_type:
        sql += " AND type = ?"
        params.append(event_type)
    if since_seq is not None:
        sql += " AND seq > ?"
        params.append(since_seq)
    sql += " ORDER BY seq ASC"
    with _db_lock:
        rows = _get_conn().execute(sql, params).fetchall()
    return [
        {
            "session_id": r["session_id"],
            "seq": r["seq"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _event_search_parts(event_type: str, payload: dict[str, Any]) -> tuple[str, str]:
    if event_type == "assistant.delta":
        return "assistant", str(payload.get("text", ""))
    if event_type == "system.message":
        return "system", str(payload.get("text") or payload.get("message", ""))
    if event_type == "tool.completed":
        return "tool", str(payload.get("output", ""))
    if event_type == "tool.started":
        return "tool", (
            f"{payload.get('tool_name', '')} "
            f"{json.dumps(payload.get('tool_input', {}), ensure_ascii=False)}"
        )
    if event_type == "tool.delta" and "tool_input" in payload:
        return "tool", json.dumps(payload.get("tool_input", {}), ensure_ascii=False)
    return "", ""


_event_search_text = _event_search_parts


def search_events(query: str) -> list[dict[str, Any]]:
    _ensure_initialized()
    needle = query.strip()
    if not needle:
        return []

    with _db_lock:
        c = _get_conn()
        if _check_fts5():
            return _search_fts5(c, needle)
        return _search_linear(c, needle)


def _search_fts5(c: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    escaped = query.replace('"', '""')
    fts_query = f'"{escaped}"'
    try:
        rows = c.execute(
            """
            SELECT
                session_id,
                seq,
                role,
                created_at,
                snippet(events_fts, 1, '<b>', '</b>', '…', 16) AS snippet
            FROM events_fts
            WHERE events_fts MATCH ?
            ORDER BY rank
            LIMIT 200
            """,
            (fts_query,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        log.warning("FTS5 query failed, falling back to linear: %s", exc)
        return _search_linear(c, query)

    return [
        {
            "session_id": r["session_id"],
            "session_title": r["session_id"][:8],
            "message_id": r["seq"],
            "snippet": r["snippet"],
            "role": r["role"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _search_linear(c: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    needle = query.lower()
    rows = c.execute(
        "SELECT * FROM events ORDER BY created_at DESC, id DESC"
    ).fetchall()

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for r in rows:
        payload = json.loads(r["payload"])
        role, haystack = _event_search_parts(r["type"], payload)
        if not haystack:
            continue

        low = haystack.lower()
        idx = low.find(needle)
        if idx == -1:
            continue

        key = (r["session_id"], r["seq"])
        if key in seen:
            continue
        seen.add(key)

        start = max(0, idx - 60)
        end = min(len(haystack), idx + len(query) + 60)
        snippet = haystack[start:end].replace("\n", " ").strip()

        results.append(
            {
                "session_id": r["session_id"],
                "session_title": r["session_id"][:8],
                "message_id": r["seq"],
                "snippet": snippet,
                "role": role,
                "created_at": r["created_at"],
            }
        )

    return results
