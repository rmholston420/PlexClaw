"""Append-only SQLite event store for replay and audit."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("plexclaw_events.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_seq "
            "ON events (session_id, seq)"
        )


def append_event(
    session_id: str,
    seq: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (session_id, seq, type, payload) VALUES (?,?,?,?)",
            (session_id, seq, event_type, json.dumps(payload)),
        )


def query_events(
    session_id: str,
    event_type: Optional[str] = None,
    since_seq: Optional[int] = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM events WHERE session_id = ?"
    params: list[Any] = [session_id]
    if event_type:
        sql += " AND type = ?"
        params.append(event_type)
    if since_seq is not None:
        sql += " AND seq > ?"
        params.append(since_seq)
    sql += " ORDER BY seq ASC"
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
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
