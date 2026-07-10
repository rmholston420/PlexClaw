from __future__ import annotations

from fastapi import HTTPException

import app.fs_routes as fs_routes


def test_safe_path_defaults_to_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(fs_routes, "FS_ROOT", root.resolve())

    result = fs_routes._safe_path(None)

    assert result == root.resolve()


def test_safe_path_allows_child(tmp_path, monkeypatch):
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "FS_ROOT", root.resolve())

    result = fs_routes._safe_path(str(child))

    assert result == child.resolve()


def test_safe_path_rejects_escape(tmp_path, monkeypatch):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(fs_routes, "FS_ROOT", root.resolve())

    try:
        fs_routes._safe_path(str(outside))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected HTTPException for escaped path")


def test_browse_parent_does_not_escape_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    monkeypatch.setattr(fs_routes, "FS_ROOT", root.resolve())

    result = fs_routes._safe_path(str(child))
    assert result == child.resolve()
    assert fs_routes._is_within_root(child.resolve().parent, root.resolve())
