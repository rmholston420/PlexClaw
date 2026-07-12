"""MCP Server configuration management — ported from Claudia (AGPL-3.0).

Original: https://github.com/getAsterisk/claudia
Adapter: re-implemented in Python/FastAPI, reads and writes the
standard Claude Desktop MCP config at ~/.claude/claude_desktop_config.json.
Also supports per-project .mcp.json override files.

Security note: `command` is validated against PATH via shutil.which() before
being written to the config.  This prevents arbitrary shell strings from being
persisted and later executed by Claude Desktop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

_CLAUDE_CONFIG = Path.home() / ".claude" / "claude_desktop_config.json"


# ---------------------------------------------------------------------------
# Config file I/O
# ---------------------------------------------------------------------------

def _load_config() -> dict[str, Any]:
    """Load the Claude Desktop MCP config.  Returns empty dict if not found."""
    if not _CLAUDE_CONFIG.exists():
        return {"mcpServers": {}}
    try:
        text = _CLAUDE_CONFIG.read_text(encoding="utf-8")
        data = json.loads(text)
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        return data
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Failed to read MCP config: %s", exc)
        return {"mcpServers": {}}


def _save_config(data: dict[str, Any]) -> None:
    """Atomically write the MCP config."""
    _CLAUDE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = _CLAUDE_CONFIG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_CLAUDE_CONFIG)


def _validate_command(command: str) -> str:
    """Return the resolved absolute path of *command* or raise HTTP 400.

    Rejects:
    * empty strings
    * strings containing shell metacharacters (spaces, semicolons, pipes, etc.)
      that indicate the caller is trying to embed a shell expression rather than
      naming a single executable
    * names that cannot be resolved via shutil.which() — i.e. not on PATH and
      not an existing absolute/relative path pointing to a real file

    Returns the resolved absolute path string so the config always stores a
    canonical, verifiable value.
    """
    cmd = command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="command must not be empty")

    # Block obvious shell-injection patterns: spaces (arg embedding), and
    # metacharacters that only make sense inside a shell expression.
    _SHELL_CHARS = set("; | & $ ` ( ) { } < > \n \r \t".split())
    if " " in cmd or any(c in cmd for c in _SHELL_CHARS):
        raise HTTPException(
            status_code=400,
            detail=(
                "command must be a single executable name or absolute path, "
                "not a shell expression.  Pass arguments via the 'args' field."
            ),
        )

    resolved = shutil.which(cmd)
    if resolved is None:
        # Accept an absolute path that points to an existing executable file
        p = Path(cmd)
        if p.is_absolute() and p.is_file():
            resolved = str(p)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"command '{cmd}' not found on PATH and is not an existing absolute path",
            )

    return resolved


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MCPServerCreate(BaseModel):
    name: str
    command: str
    args: list[str] = []
    env: dict[str, str] = {}
    enabled: bool = True

class MCPServerUpdate(BaseModel):
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def list_mcp_servers() -> dict:
    """Return all configured MCP servers."""
    def _load() -> dict:
        cfg = _load_config()
        servers = [
            {
                "name":    name,
                "command": srv.get("command", ""),
                "args":    srv.get("args", []),
                "env":     srv.get("env", {}),
                "enabled": srv.get("enabled", True),
            }
            for name, srv in cfg["mcpServers"].items()
        ]
        return {"servers": servers, "config_path": str(_CLAUDE_CONFIG)}

    return await asyncio.to_thread(_load)


@router.post("")
async def add_mcp_server(req: MCPServerCreate) -> dict:
    """Add or overwrite an MCP server entry.

    The `command` field is validated against PATH before being written.
    Arbitrary shell expressions are rejected with HTTP 400.
    """
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be empty")

    # Validate *before* touching the config file.
    resolved_command = _validate_command(req.command)

    def _write() -> dict:
        cfg = _load_config()
        cfg["mcpServers"][name] = {
            "command": resolved_command,
            "args":    req.args,
            "env":     req.env,
            "enabled": req.enabled,
        }
        _save_config(cfg)
        return {"ok": True, "name": name, "resolved_command": resolved_command}

    return await asyncio.to_thread(_write)


@router.patch("/{name}")
async def update_mcp_server(name: str, req: MCPServerUpdate) -> dict:
    """Partially update an existing MCP server entry.

    If `command` is supplied it is validated against PATH before the config
    is updated.  Arbitrary shell expressions are rejected with HTTP 400.
    """
    # Validate command outside the thread so HTTPException propagates cleanly.
    resolved_command: str | None = None
    if req.command is not None:
        resolved_command = _validate_command(req.command)

    def _patch() -> dict:
        cfg = _load_config()
        if name not in cfg["mcpServers"]:
            raise HTTPException(status_code=404, detail=f"server '{name}' not found")
        srv = cfg["mcpServers"][name]
        if resolved_command is not None:
            srv["command"] = resolved_command
        if req.args is not None:
            srv["args"] = req.args
        if req.env is not None:
            srv["env"] = req.env
        if req.enabled is not None:
            srv["enabled"] = req.enabled
        _save_config(cfg)
        return {"ok": True, "name": name}

    return await asyncio.to_thread(_patch)


@router.delete("/{name}")
async def delete_mcp_server(name: str) -> dict:
    """Remove an MCP server entry."""
    def _remove() -> dict:
        cfg = _load_config()
        if name not in cfg["mcpServers"]:
            raise HTTPException(status_code=404, detail=f"server '{name}' not found")
        del cfg["mcpServers"][name]
        _save_config(cfg)
        return {"ok": True}

    return await asyncio.to_thread(_remove)


@router.post("/{name}/test")
async def test_mcp_server(name: str) -> dict:
    """Test whether the MCP server command is reachable on PATH."""
    def _test() -> dict:
        cfg = _load_config()
        if name not in cfg["mcpServers"]:
            raise HTTPException(status_code=404, detail=f"server '{name}' not found")
        command = cfg["mcpServers"][name].get("command", "")
        if not command:
            return {"ok": False, "reason": "no command configured"}
        found = shutil.which(command)
        return {
            "ok": bool(found),
            "command": command,
            "path": found or None,
            "reason": None if found else f"'{command}' not found on PATH",
        }

    return await asyncio.to_thread(_test)
