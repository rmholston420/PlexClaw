"""Git operations exposed as REST endpoints — ported from CloudCLI (GPL-3.0).

Original: https://github.com/siteboon/claudecodeui
Adapter: re-implemented in Python subprocess, integrated with PlexClaw
filesystem jail (_resolve_safe_path) and session cwd.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.fs_routes import _resolve_safe_path

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/git", tags=["git"])

_GIT = shutil.which("git") or "git"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command synchronously, capturing stdout/stderr."""
    return subprocess.run(
        [_GIT, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=15,
    )


async def _agit(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run git in a thread to avoid blocking the asyncio loop."""
    return await asyncio.to_thread(_git, *args, cwd=cwd)


def _require_git_repo(path: Path) -> Path:
    """Walk upward to find the git root, raise 404 if none found."""
    current = path if path.is_dir() else path.parent
    for _ in range(20):
        if (current / ".git").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise HTTPException(
        status_code=404,
        detail=f"no git repository found at or above: {path}",
    )


def _parse_status(output: str) -> list[dict[str, str]]:
    """Parse `git status --porcelain=v1` output into structured entries."""
    files: list[dict[str, str]] = []
    for line in output.splitlines():
        if len(line) < 2:
            continue
        xy = line[:2]
        rest = line[3:]
        # Handle renames: "old -> new"
        if " -> " in rest:
            _, rest = rest.split(" -> ", 1)
        files.append({"status": xy.strip(), "path": rest.strip()})
    return files


def _parse_log(output: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\x1f", 4)
        if len(parts) < 5:
            continue
        entries.append({
            "hash":    parts[0],
            "short":   parts[1],
            "author":  parts[2],
            "date":    parts[3],
            "message": parts[4],
        })
    return entries


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class StageRequest(BaseModel):
    paths: list[str]
    session_id: str | None = None

class UnstageRequest(BaseModel):
    paths: list[str]
    session_id: str | None = None

class CommitRequest(BaseModel):
    message: str
    session_id: str | None = None

class CheckoutRequest(BaseModel):
    branch: str
    create: bool = False
    session_id: str | None = None

class DiffRequest(BaseModel):
    path: str | None = None
    staged: bool = False
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status")
async def git_status(
    path: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
) -> dict:
    """Return working-tree status for the git repo at or above `path`."""
    resolved, _root = _resolve_safe_path(path, session_id=session_id)
    repo = _require_git_repo(resolved)

    result = await _agit("status", "--porcelain=v1", "--branch", cwd=repo)
    lines = result.stdout.splitlines()

    branch_line = lines[0] if lines else ""
    branch = (
        branch_line.lstrip("# ").split("...")[0]
        if branch_line.startswith("## ")
        else "(detached)"
    )
    if branch.startswith("## "):
        branch = branch[3:].split("...")[0]

    file_lines = "\n".join(lines[1:])
    files = _parse_status(file_lines)

    staged   = [f for f in files if f["status"][0] not in (" ", "?")]
    unstaged = [
        f for f in files
        if f["status"] == "??"
        or (
            len(f["status"]) > 1
            and f["status"][1] not in (" ",)
        )
    ]

    return {
        "repo": str(repo),
        "branch": branch,
        "staged": staged,
        "unstaged": unstaged,
        "clean": not files,
    }


@router.get("/log")
async def git_log(
    path: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list:
    """Return the recent commit log."""
    resolved, _root = _resolve_safe_path(path, session_id=session_id)
    repo = _require_git_repo(resolved)

    fmt = "%H%x1f%h%x1f%an%x1f%ai%x1f%s"
    result = await _agit(
        "log", f"--pretty=format:{fmt}", f"-{limit}", cwd=repo
    )
    return _parse_log(result.stdout)


@router.get("/diff")
async def git_diff(
    path: str | None = Query(default=None),
    staged: bool = Query(default=False),
    file: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
) -> dict:
    """Return unified diff for working tree or staging area."""
    resolved, _root = _resolve_safe_path(path, session_id=session_id)
    repo = _require_git_repo(resolved)

    args = ["diff"]
    if staged:
        args.append("--staged")
    args += ["--", file] if file else []

    result = await _agit(*args, cwd=repo)
    return {"diff": result.stdout, "repo": str(repo)}


@router.get("/branches")
async def git_branches(
    path: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
) -> dict:
    """List local branches and identify the current branch."""
    resolved, _root = _resolve_safe_path(path, session_id=session_id)
    repo = _require_git_repo(resolved)

    result = await _agit(
        "branch",
        "--list",
        "--format=%(refname:short)|%(HEAD)",
        cwd=repo,
    )
    branches: list[dict[str, Any]] = []
    current = None
    for line in result.stdout.splitlines():
        parts = line.split("|")
        name = parts[0].strip()
        is_current = len(parts) > 1 and parts[1].strip() == "*"
        if is_current:
            current = name
        branches.append({"name": name, "current": is_current})

    return {"branches": branches, "current": current, "repo": str(repo)}


@router.post("/stage")
async def git_stage(req: StageRequest) -> dict:
    """Stage the specified file paths."""
    if not req.paths:
        raise HTTPException(status_code=400, detail="paths must not be empty")
    resolved, _root = _resolve_safe_path(None, session_id=req.session_id)
    repo = _require_git_repo(resolved)
    result = await _agit("add", "--", *req.paths, cwd=repo)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=result.stderr.strip())
    return {"ok": True, "repo": str(repo)}


@router.post("/unstage")
async def git_unstage(req: UnstageRequest) -> dict:
    """Unstage the specified file paths."""
    if not req.paths:
        raise HTTPException(status_code=400, detail="paths must not be empty")
    resolved, _root = _resolve_safe_path(None, session_id=req.session_id)
    repo = _require_git_repo(resolved)
    result = await _agit("restore", "--staged", "--", *req.paths, cwd=repo)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=result.stderr.strip())
    return {"ok": True}


@router.post("/commit")
async def git_commit(req: CommitRequest) -> dict:
    """Commit staged changes."""
    msg = req.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="commit message must not be empty")
    resolved, _root = _resolve_safe_path(None, session_id=req.session_id)
    repo = _require_git_repo(resolved)
    result = await _agit("commit", "-m", msg, cwd=repo)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=result.stderr.strip())
    # Extract the short hash from "[branch abc1234] message"
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    return {"ok": True, "output": first_line}


@router.post("/checkout")
async def git_checkout(req: CheckoutRequest) -> dict:
    """Checkout or create a branch."""
    branch = req.branch.strip()
    if not branch:
        raise HTTPException(status_code=400, detail="branch must not be empty")
    resolved, _root = _resolve_safe_path(None, session_id=req.session_id)
    repo = _require_git_repo(resolved)
    args = ["checkout", "-b", branch] if req.create else ["checkout", branch]
    result = await _agit(*args, cwd=repo)
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=result.stderr.strip())
    return {"ok": True, "branch": branch}
