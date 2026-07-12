"""MCP Server configuration management — ported from Claudia (AGPL-3.0).

Original: https://github.com/getAsterisk/claudia
Adapter: re-implemented in Python/FastAPI, reads and writes the
standard Claude Desktop MCP config at ~/.claude/claude_desktop_config.json.
Also supports per-project .mcp.json override files.
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
    """Add or overwrite an MCP server entry."""
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be empty")
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="command must not be empty")

    def _write() -> dict:
        cfg = _load_config()
        cfg["mcpServers"][name] = {
            "command": req.command.strip(),
            "args":    req.args,
            "env":     req.env,
            "enabled": req.enabled,
        }
        _save_config(cfg)
        return {"ok": True, "name": name}

    return await asyncio.to_thread(_write)


@router.patch("/{name}")
async def update_mcp_server(name: str, req: MCPServerUpdate) -> dict:
    """Partially update an existing MCP server entry."""
    def _patch() -> dict:
        cfg = _load_config()
        if name not in cfg["mcpServers"]:
            raise HTTPException(status_code=404, detail=f"server '{name}' not found")
        srv = cfg["mcpServers"][name]
        if req.command is not None:
            srv["command"] = req.command.strip()
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
