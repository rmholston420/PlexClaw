from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app import runtime_sdk

router = APIRouter(prefix="/api/fs", tags=["fs"])

FS_ROOT = Path.cwd().resolve()

MAX_READ_BYTES = 512 * 1024  # 512 KB hard cap


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _get_fs_root(session_id: str | None) -> Path:
    if session_id:
        session = runtime_sdk.get_session(session_id)
        if session and session.cwd:
            return Path(session.cwd).expanduser().resolve()
    return FS_ROOT.resolve()


def _resolve_safe_path(path: str | None, session_id: str | None = None) -> tuple[Path, Path]:
    root = _get_fs_root(session_id)

    if not path:
        return root, root

    candidate = Path(path).expanduser()
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"path does not exist: {resolved}")
    if not _is_within_root(resolved, root):
        raise HTTPException(status_code=403, detail=f"path escapes allowed root: {resolved}")
    return resolved, root


def _safe_path(path: str | None) -> Path:
    resolved, _root = _resolve_safe_path(path, session_id=None)
    return resolved


@router.get("/browse")
async def browse(
    path: str | None = Query(default=None, description="Path to browse"),
    session_id: str | None = Query(default=None, description="Optional live session id"),
) -> dict:
    base, root = _resolve_safe_path(path, session_id=session_id)
    if not base.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {base}")

    entries: list[dict] = []

    parent = base.parent
    if parent != base and _is_within_root(parent, root):
        stat = parent.stat()
        entries.append(
            {
                "name": "..",
                "is_dir": True,
                "size": None,
                "modified": int(stat.st_mtime),
            }
        )

    for entry in os.scandir(base):
        try:
            st = entry.stat()
        except FileNotFoundError:
            continue
        entries.append(
            {
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": None if entry.is_dir() else st.st_size,
                "modified": int(st.st_mtime),
            }
        )

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return {"path": str(base), "root": str(root), "entries": entries}


@router.get("/read")
async def read_file(
    path: str = Query(..., description="Absolute or relative path to read"),
    session_id: str | None = Query(default=None, description="Optional live session id"),
) -> dict:
    """Return the text contents of a file within the active filesystem root.

    Returns:
        path      – resolved absolute path
        content   – UTF-8 text content
        size      – byte size of the file
        truncated – True when the file was cut at MAX_READ_BYTES
    """
    p, _root = _resolve_safe_path(path, session_id=session_id)
    if p.is_dir():
        raise HTTPException(status_code=400, detail=f"path is a directory: {p}")

    size = p.stat().st_size
    truncated = size > MAX_READ_BYTES

    try:
        raw = p.read_bytes()[:MAX_READ_BYTES]
        content = raw.decode("utf-8", errors="replace")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"permission denied: {p}") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"read error: {exc}") from exc

    return {
        "path": str(p),
        "content": content,
        "size": size,
        "truncated": truncated,
    }


@router.get("/git-roots")
async def git_roots(
    start: str | None = Query(default=None),
    max_depth: int = Query(default=3, ge=1, le=6),
    session_id: str | None = Query(default=None, description="Optional live session id"),
) -> dict:
    current, root = _resolve_safe_path(start, session_id=session_id)
    roots: list[str] = []
    depth = 0

    while True:
        if depth > max_depth:
            break
        if not _is_within_root(current, root):
            break

        git_dir = current / ".git"
        if git_dir.exists() and git_dir.is_dir():
            roots.append(str(current))

        parent = current.parent
        if parent == current or not _is_within_root(parent, root):
            break
        current = parent
        depth += 1

    return {"root": str(root), "roots": sorted(set(roots))}
