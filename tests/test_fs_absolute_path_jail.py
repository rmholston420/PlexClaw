from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.fs_routes as fs_routes
from app.main import app

client = TestClient(app)


def test_absolute_path_within_root_is_allowed(tmp_path: Path) -> None:
    """An absolute path that resolves inside the session root must succeed."""
    sentinel = tmp_path / "hello.txt"
    sentinel.write_text("hello")

    original = fs_routes.get_default_fs_root
    fs_routes.get_default_fs_root = lambda: tmp_path.resolve()
    try:
        resp = client.get("/api/fs/read", params={"path": str(sentinel.resolve())})
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "hello"
        assert data["path"] == str(sentinel.resolve())
    finally:
        fs_routes.get_default_fs_root = original


def test_absolute_path_outside_root_is_rejected(tmp_path: Path) -> None:
    """An absolute path that escapes the jail must return 403, not 200."""
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("nope")

    original = fs_routes.get_default_fs_root
    fs_routes.get_default_fs_root = lambda: tmp_path.resolve()
    try:
        resp = client.get("/api/fs/read", params={"path": str(outside.resolve())})
        assert resp.status_code == 403
        assert "escapes allowed root" in resp.text
    finally:
        fs_routes.get_default_fs_root = original
