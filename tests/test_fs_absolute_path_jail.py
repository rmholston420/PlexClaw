"""Regression tests for fs_routes absolute-path jail bypass fix.

Before the fix, passing an absolute path to _resolve_safe_path would
skip the jail check, allowing reads of any world-readable file on the
host (e.g. /etc/passwd).  These tests ensure the fix holds.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import fs_routes

client = TestClient(app, raise_server_exceptions=True)


def test_absolute_path_within_root_is_allowed(tmp_path: Path) -> None:
    """An absolute path that resolves inside the session root must succeed."""
    # Write a file inside the tmp_path jail
    sentinel = tmp_path / "hello.txt"
    sentinel.write_text("hello")

    # Temporarily override FS_ROOT to tmp_path so the test is deterministic
    original_root = fs_routes.FS_ROOT
    fs_routes.FS_ROOT = tmp_path
    try:
        resp = client.get("/api/fs/read", params={"path": str(sentinel)})
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello"
    finally:
        fs_routes.FS_ROOT = original_root


def test_absolute_path_outside_root_is_rejected(tmp_path: Path) -> None:
    """An absolute path that escapes the jail must return 403, not 200."""
    original_root = fs_routes.FS_ROOT
    fs_routes.FS_ROOT = tmp_path
    try:
        # /tmp itself is outside tmp_path (tmp_path is a subdirectory of /tmp)
        outside = tmp_path.parent
        resp = client.get("/api/fs/browse", params={"path": str(outside)})
        assert resp.status_code == 403, (
            f"Expected 403 for path={outside!s} with root={tmp_path!s}, "
            f"got {resp.status_code}: {resp.text}"
        )
    finally:
        fs_routes.FS_ROOT = original_root
