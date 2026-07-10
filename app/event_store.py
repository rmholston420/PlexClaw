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


def _event_search_text(event_type: str, payload: dict[str, Any]) -> tuple[str, str]:
    if event_type == "assistant.delta":
        return "assistant", str(payload.get("text", ""))
    if event_type == "system.message":
        return "system", str(payload.get("text") or payload.get("message", ""))
    if event_type == "tool.completed":
        return "tool", str(payload.get("output", ""))
    if event_type == "tool.started":
        return "tool", f"{payload.get('tool_name', '')} {json.dumps(payload.get('tool_input', {}), ensure_ascii=False)}"
    return "", ""


def search_events(query: str) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    if not needle:
        return []

    with _conn() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY created_at DESC, id DESC").fetchall()

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for r in rows:
        payload = json.loads(r["payload"])
        role, haystack = _event_search_text(r["type"], payload)
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
