from __future__ import annotations

import json
import sqlite3

from app import event_store


def test_search_linear_rows_matches_without_connection() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        (
            "INSERT INTO events (session_id, seq, type, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?)"
        ),
        (
            "session-1",
            1,
            "tool.completed",
            json.dumps(
                {
                    "tool_name": "Read",
                    "output": "Found README instructions here",
                    "is_error": False,
                }
            ),
            "2026-07-11 22:00:00",
        ),
    )
    rows = conn.execute(
        "SELECT * FROM events ORDER BY created_at DESC, id DESC"
    ).fetchall()

    results = event_store._search_linear_rows(rows, "README")

    assert len(results) == 1
    assert results[0]["session_id"] == "session-1"
    assert "README" in results[0]["snippet"]
