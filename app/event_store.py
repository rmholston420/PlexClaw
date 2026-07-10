"""Append-only SQLite event store for replay and audit.

Changes vs original:
- Single module-level connection (re-opened only if DB path changes) with
  WAL journal mode and a 32 MB cache; eliminates per-call connect overhead.
- FTS5 virtual table `events_fts` shadows the `events` table for sub-ms
  keyword search regardless of row count.  Falls back to the original
  linear scan if the SQLite build omits FTS5.
- `search_events` uses FTS5 MATCH when available; plain LIKE scan otherwise.
- Schema migration: `init_db()` is idempotent and upgrades existing DBs.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Optional

log = logging.getLogger(__name__)

DB_PATH = Path("plexclaw_events.db")

# ---------------------------------------------------------------------------
# Persistent connection — one per process; thread-safe via _db_lock
# ---------------------------------------------------------------------------

_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[Path] = None
_db_lock = Lock()
_fts_available: Optional[bool] = None


def _get_conn() -> sqlite3.Connection:
    """Return (or lazily open) the module-level connection."""
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
        c.execute("PRAGMA cache_size=-32768")  # 32 MB page cache
        c.execute("PRAGMA synchronous=NORMAL")
        _conn = c
        _conn_path = DB_PATH
    return _conn


def _check_fts5() -> bool:
    """Return True if SQLite was compiled with the FTS5 extension."""
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


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create / migrate tables.  Safe to call multiple times."""
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
            "CREATE INDEX IF NOT EXISTS idx_session_seq "
            "ON events (session_id, seq)"
        )
        # Add a covering index for the full-table scan fallback path
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_desc "
            "ON events (created_at DESC, id DESC)"
        )

        if _check_fts5():
            # FTS5 content table mirrors `events`; updated via triggers.
            c.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
                USING fts5(
                    role,
                    body,
                    session_id UNINDEXED,
                    seq        UNINDEXED,
                    event_type UNINDEXED,
                    created_at UNINDEXED,
                    content    = events,
                    content_rowid = id
                )
                """
            )
            # Insert trigger
            c.execute(
                """
                CREATE TRIGGER IF NOT EXISTS events_fts_ai
                AFTER INSERT ON events BEGIN
                    INSERT INTO events_fts(
                        rowid, role, body,
                        session_id, seq, event_type, created_at
                    )
                    VALUES (
                        new.id,
                        _plexclaw_fts_role(new.type),
                        _plexclaw_fts_body(new.type, new.payload),
                        new.session_id, new.seq, new.type, new.created_at
                    );
                END
                """
            )

        c.commit()

        # Pre-populate FTS index from existing rows if it is empty
        if _check_fts5():
            try:
                (existing,) = c.execute(
                    "SELECT COUNT(*) FROM events_fts"
                ).fetchone()
                if existing == 0:
                    rows = c.execute(
                        "SELECT id, type, payload, session_id, seq, created_at "
                        "FROM events"
                    ).fetchall()
                    for r in rows:
                        role, body = _event_search_parts(
                            r["type"], json.loads(r["payload"])
                        )
                        c.execute(
                            "INSERT INTO events_fts("
                            "  rowid, role, body, session_id, seq, event_type, created_at"
                            ") VALUES (?,?,?,?,?,?,?)",
                            (
                                r["id"],
                                role,
                                body,
                                r["session_id"],
                                r["seq"],
                                r["type"],
                                r["created_at"],
                            ),
                        )
                    c.commit()
                    log.info(
                        "Backfilled %d events into FTS5 index", len(rows)
                    )
            except Exception as exc:
                log.warning("FTS backfill skipped: %s", exc)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def append_event(
    session_id: str,
    seq: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    payload_json = json.dumps(payload)
    with _db_lock:
        c = _get_conn()
        cursor = c.execute(
            "INSERT INTO events (session_id, seq, type, payload) VALUES (?,?,?,?)",
            (session_id, seq, event_type, payload_json),
        )
        row_id = cursor.lastrowid

        # Manually maintain FTS when triggers can't reference custom functions
        if _check_fts5() and row_id:
            role, body = _event_search_parts(event_type, payload)
            if body:
                try:
                    c.execute(
                        "INSERT INTO events_fts("
                        "  rowid, role, body, session_id, seq, event_type, created_at"
                        ") VALUES (?,?,?,?,?,?,datetime('now'))",
                        (row_id, role, body, session_id, seq, event_type),
                    )
                except Exception as exc:
                    log.debug("FTS insert skipped: %s", exc)

        c.commit()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------


def _event_search_parts(
    event_type: str, payload: dict[str, Any]
) -> tuple[str, str]:
    """Return (role, searchable_text) for an event."""
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
    return "", ""


# Keep the old name for backward compat with existing callers / tests
_event_search_text = _event_search_parts


def search_events(query: str) -> list[dict[str, Any]]:
    needle = query.strip()
    if not needle:
        return []

    with _db_lock:
        c = _get_conn()

        if _check_fts5():
            return _search_fts5(c, needle)
        return _search_linear(c, needle)


def _search_fts5(
    c: sqlite3.Connection, query: str
) -> list[dict[str, Any]]:
    """FTS5-backed search with snippet extraction."""
    # Escape FTS5 special chars; wrap in quotes for phrase search
    escaped = query.replace('"', '""')
    fts_query = f'"{escaped}"'

    try:
        rows = c.execute(
            """
            SELECT
                f.session_id,
                f.seq,
                f.role,
                f.event_type,
                f.created_at,
                snippet(events_fts, 1, '<b>', '</b>', '…', 16) AS snippet
            FROM events_fts f
            WHERE events_fts MATCH ?
            ORDER BY rank
            LIMIT 200
            """,
            (fts_query,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        log.warning("FTS5 query failed, falling back to linear: %s", exc)
        return _search_linear(c, query)

    results = []
    for r in rows:
        results.append(
            {
                "session_id": r[0],
                "session_title": r[0][:8],
                "message_id": r[1],
                "snippet": r[5],
                "role": r[2],
                "created_at": r[4],
            }
        )
    return results


def _search_linear(
    c: sqlite3.Connection, query: str
) -> list[dict[str, Any]]:
    """Original O(n) fallback scan — used when FTS5 is unavailable."""
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
