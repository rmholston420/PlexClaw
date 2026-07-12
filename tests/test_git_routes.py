"""Tests for app/git_routes.py — git operations REST API."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture()
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal git repository and point the FS root at it."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(tmp_path), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path), check=True, capture_output=True,
    )
    # Create an initial commit so the repo is valid
    readme = tmp_path / "README.md"
    readme.write_text("# test repo\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(tmp_path), check=True, capture_output=True,
    )
    monkeypatch.setenv("PLEXCLAW_FS_ROOT", str(tmp_path))
    return tmp_path


def test_git_status_clean(git_repo: Path):
    r = client.get("/api/git/status")
    assert r.status_code == 200
    data = r.json()
    assert data["clean"] is True
    assert "branch" in data


def test_git_status_with_change(git_repo: Path):
    (git_repo / "new.txt").write_text("hello")
    r = client.get("/api/git/status")
    assert r.status_code == 200
    data = r.json()
    assert not data["clean"]
    assert any(f["path"] == "new.txt" for f in data["unstaged"])


def test_git_log(git_repo: Path):
    r = client.get("/api/git/log")
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) >= 1
    assert "hash" in entries[0]
    assert "message" in entries[0]


def test_git_log_limit(git_repo: Path):
    r = client.get("/api/git/log?limit=1")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_git_branches(git_repo: Path):
    r = client.get("/api/git/branches")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["branches"], list)
    assert data["current"] is not None


def test_git_stage_and_status(git_repo: Path):
    (git_repo / "staged.txt").write_text("content")
    r = client.post("/api/git/stage", json={"paths": ["staged.txt"]})
    assert r.status_code == 200
    assert r.json()["ok"] is True

    status = client.get("/api/git/status").json()
    assert any(f["path"] == "staged.txt" for f in status["staged"])


def test_git_commit(git_repo: Path):
    (git_repo / "commit_me.txt").write_text("data")
    client.post("/api/git/stage", json={"paths": ["commit_me.txt"]})
    r = client.post("/api/git/commit", json={"message": "test commit"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_git_commit_empty_message(git_repo: Path):
    r = client.post("/api/git/commit", json={"message": "   "})
    assert r.status_code == 400


def test_git_stage_empty_paths(git_repo: Path):
    r = client.post("/api/git/stage", json={"paths": []})
    assert r.status_code == 400


def test_git_diff(git_repo: Path):
    (git_repo / "diff_me.txt").write_text("original")
    subprocess.run(
        ["git", "add", "."],
        cwd=str(git_repo),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=str(git_repo),
        check=True,
        capture_output=True,
    )
    (git_repo / "diff_me.txt").write_text("modified")
    r = client.get("/api/git/diff")
    assert r.status_code == 200
    data = r.json()
    assert "diff" in data


def test_git_status_no_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PLEXCLAW_FS_ROOT", str(tmp_path))
    r = client.get("/api/git/status")
    assert r.status_code == 404
