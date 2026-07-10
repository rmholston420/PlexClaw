from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/fs", tags=["fs"])


def _safe_path(path: str | None) -> Path:
    if not path:
        return Path.cwd()
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"path does not exist: {p}")
    return p


@router.get("/browse")
async def browse(
    path: str | None = Query(default=None, description="Path to browse"),
) -> dict:
    base = _safe_path(path)
    if not base.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {base}")

    entries: list[dict] = []

    parent = base.parent
    if parent != base:
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
    return {"path": str(base), "entries": entries}


@router.get("/git-roots")
async def git_roots(
    start: str | None = Query(default=None),
    max_depth: int = Query(default=3, ge=1, le=6),
) -> dict:
    current = _safe_path(start)
    roots: list[str] = []
    depth = 0

    while True:
        if depth > max_depth:
            break
        git_dir = current / ".git"
        if git_dir.exists() and git_dir.is_dir():
            roots.append(str(current))

        parent = current.parent
        if parent == current:
            break
        current = parent
        depth += 1

    return {"roots": sorted(set(roots))}
