from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import fs_routes


def test_is_within_root_false_for_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    assert fs_routes._is_within_root(outside, root) is False


def test_get_fs_root_uses_session_cwd(monkeypatch, tmp_path):
    session_root = tmp_path / "session-root"
    session_root.mkdir()

    monkeypatch.setattr(
        fs_routes.runtime_sdk,
        "get_session",
        lambda session_id: SimpleNamespace(cwd=str(session_root)),
    )

    assert fs_routes._get_fs_root("sess-1") == session_root.resolve()


def test_get_fs_root_falls_back_when_session_has_no_cwd(monkeypatch, tmp_path):
    fallback = tmp_path / "fallback"
    fallback.mkdir()

    monkeypatch.setattr(fs_routes, "get_default_fs_root()", fallback)
    monkeypatch.setattr(
        fs_routes.runtime_sdk,
        "get_session",
        lambda session_id: SimpleNamespace(cwd=None),
    )

    assert fs_routes._get_fs_root("sess-2") == fallback.resolve()


def test_resolve_safe_path_none_returns_root(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    resolved, resolved_root = fs_routes._resolve_safe_path(None)

    assert resolved == root.resolve()
    assert resolved_root == root.resolve()


def test_resolve_safe_path_nonexistent_raises_400(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    with pytest.raises(HTTPException) as exc:
        fs_routes._resolve_safe_path("missing.txt")

    assert exc.value.status_code == 400
    assert "path does not exist" in exc.value.detail


def test_resolve_safe_path_absolute_escape_raises_403(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    with pytest.raises(HTTPException) as exc:
        fs_routes._resolve_safe_path(str(outside))

    assert exc.value.status_code == 403
    assert "path escapes allowed root" in exc.value.detail


@pytest.mark.asyncio
async def test_browse_rejects_file_path(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "note.txt"
    file_path.write_text("hello")
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    with pytest.raises(HTTPException) as exc:
        await fs_routes.browse(path="note.txt")

    assert exc.value.status_code == 400
    assert "not a directory" in exc.value.detail


@pytest.mark.asyncio
async def test_browse_includes_parent_entry_within_root(monkeypatch, tmp_path):
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    out = await fs_routes.browse(path="child")

    assert out["path"] == str(child.resolve())
    assert out["root"] == str(root.resolve())
    assert out["entries"][0]["name"] == ".."
    assert out["entries"][0]["is_dir"] is True


@pytest.mark.asyncio
async def test_browse_truncates_after_2000_entries(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    original_scandir = fs_routes.os.scandir

    class FakeDirEntry:
        def __init__(self, idx: int):
            self.name = f"f{idx:04d}.txt"
            self._idx = idx

        def stat(self):
            return SimpleNamespace(st_size=self._idx, st_mtime=1000 + self._idx)

        def is_dir(self):
            return False

    def fake_scandir(path):
        return [FakeDirEntry(i) for i in range(2005)]

    monkeypatch.setattr(fs_routes.os, "scandir", fake_scandir)
    try:
        out = await fs_routes.browse(path=None)
    finally:
        monkeypatch.setattr(fs_routes.os, "scandir", original_scandir)

    assert out["truncated"] is True
    assert len(out["entries"]) == 2000


@pytest.mark.asyncio
async def test_browse_skips_file_not_found_entries(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    class GoodEntry:
        name = "good.txt"

        def stat(self):
            return SimpleNamespace(st_size=3, st_mtime=123)

        def is_dir(self):
            return False

    class MissingEntry:
        name = "missing.txt"

        def stat(self):
            raise FileNotFoundError

        def is_dir(self):
            return False

    monkeypatch.setattr(
        fs_routes.os,
        "scandir",
        lambda path: [MissingEntry(), GoodEntry()],
    )

    out = await fs_routes.browse(path=None)

    names = [e["name"] for e in out["entries"]]
    assert "good.txt" in names
    assert "missing.txt" not in names


@pytest.mark.asyncio
async def test_read_file_rejects_directory(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    with pytest.raises(HTTPException) as exc:
        await fs_routes.read_file(path=".")

    assert exc.value.status_code == 400
    assert "path is a directory" in exc.value.detail


@pytest.mark.asyncio
async def test_read_file_permission_error_maps_to_403(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "secret.txt"
    file_path.write_text("secret")
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    def fake_read_bytes(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)

    with pytest.raises(HTTPException) as exc:
        await fs_routes.read_file(path="secret.txt")

    assert exc.value.status_code == 403
    assert "permission denied" in exc.value.detail


@pytest.mark.asyncio
async def test_read_file_oserror_maps_to_500(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "broken.txt"
    file_path.write_text("broken")
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    def fake_read_bytes(self):
        raise OSError("io boom")

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)

    with pytest.raises(HTTPException) as exc:
        await fs_routes.read_file(path="broken.txt")

    assert exc.value.status_code == 500
    assert "read error" in exc.value.detail


@pytest.mark.asyncio
async def test_read_file_reports_truncated_for_large_file(monkeypatch, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "big.txt"
    content = b"a" * (fs_routes.MAX_READ_BYTES + 10)
    file_path.write_bytes(content)
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    out = await fs_routes.read_file(path="big.txt")

    assert out["size"] == len(content)
    assert out["truncated"] is True
    assert len(out["content"].encode("utf-8")) == fs_routes.MAX_READ_BYTES


@pytest.mark.asyncio
async def test_git_roots_finds_containing_repo(monkeypatch, tmp_path):
    root = tmp_path / "root"
    repo = root / "repo"
    nested = repo / "a" / "b"
    (repo / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    out = await fs_routes.git_roots(start=str(nested), max_depth=3)

    assert out["root"] == str(root.resolve())
    assert out["roots"] == [str(repo.resolve())]


@pytest.mark.asyncio
async def test_git_roots_respects_max_depth(monkeypatch, tmp_path):
    root = tmp_path / "root"
    repo = root / "repo"
    nested = repo / "a" / "b" / "c"
    (repo / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    out = await fs_routes.git_roots(start=str(nested), max_depth=1)

    assert out["roots"] == []


@pytest.mark.asyncio
async def test_git_roots_returns_empty_when_no_repo_found(monkeypatch, tmp_path):
    root = tmp_path / "root"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root)

    out = await fs_routes.git_roots(start=str(nested), max_depth=3)

    assert out["root"] == str(root.resolve())
    assert out["roots"] == []
