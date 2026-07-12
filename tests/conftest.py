"""Shared pytest fixtures for PlexClaw test suite.

Provides a single autouse fixture that:
  - Clears runtime session state before each test
  - Redirects the SQLite event store to a fresh temp DB
  - Resets all module-level DB globals (conn, path, flags, init flag)
  - Tears down cleanly after each test

Individual test files may still define their own fixtures on top of this,
but they must NOT re-patch the same globals (use the shared fixture instead).
"""

from __future__ import annotations

from threading import Lock

import pytest

import app.event_store as event_store
from app import hooks
from app import runtime_sdk as runtime
from app.event_store import close_db, init_db


@pytest.fixture(autouse=True)
def reset_plexclaw_state(tmp_path, monkeypatch):
    """Isolate every test: fresh sessions dict + fresh SQLite DB."""
    # --- runtime state ---
    runtime._sessions.clear()

    # --- event store: redirect to isolated temp DB ---
    db_path = tmp_path / "test_events.db"
    monkeypatch.setattr(event_store, "DB_PATH", db_path)
    monkeypatch.setattr(event_store, "_db_lock", Lock())
    close_db()
    init_db()

    yield
    hooks.reset_hooks()

    # --- teardown ---
    runtime._sessions.clear()

    close_db()
    event_store._db_lock = Lock()
