"""Tests for GET /api/fs/read."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.fs_routes as fs_mod
from app.main import app


@pytest.fixture(autouse=True)
def _patch_fs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(fs_mod, "get_default_fs_root", lambda: tmp_path.resolve())
    yield


def test_read_text_file(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")
    client = TestClient(app)
    resp = client.get("/api/fs/read", params={"path": str(f)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "hello world"
    assert data["truncated"] is False
    assert data["size"] == len("hello world")


def test_read_directory_returns_400(tmp_path: Path):
    client = TestClient(app)
    resp = client.get("/api/fs/read", params={"path": str(tmp_path)})
    assert resp.status_code == 400


def test_read_path_escape_returns_403(tmp_path: Path):
    client = TestClient(app)
    resp = client.get("/api/fs/read", params={"path": "/etc/passwd"})
    assert resp.status_code == 403


def test_read_nonexistent_inside_root_returns_400(tmp_path: Path):
    client = TestClient(app)
    resp = client.get("/api/fs/read", params={"path": str(tmp_path / "nope.txt")})
    assert resp.status_code == 400


def test_read_truncation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(fs_mod, "MAX_READ_BYTES", 5)
    f = tmp_path / "big.txt"
    f.write_text("abcdefghij", encoding="utf-8")
    client = TestClient(app)
    resp = client.get("/api/fs/read", params={"path": str(f)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["truncated"] is True
    assert data["content"] == "abcde"


def test_read_missing_path_param_returns_422():
    client = TestClient(app)
    resp = client.get("/api/fs/read")
    assert resp.status_code == 422
