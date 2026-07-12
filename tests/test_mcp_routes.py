"""Tests for app/mcp_routes.py — MCP server config management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.mcp_routes as mcp_mod
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_mcp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake_config = tmp_path / ".claude" / "claude_desktop_config.json"
    fake_config.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mcp_mod, "_CLAUDE_CONFIG", fake_config)
    yield


def test_list_empty():
    r = client.get("/api/mcp")
    assert r.status_code == 200
    data = r.json()
    assert data["servers"] == []


def test_add_server():
    r = client.post("/api/mcp", json={
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": {},
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["name"] == "filesystem"


def test_list_after_add():
    client.post("/api/mcp", json={"name": "fs", "command": "npx", "args": []})
    r = client.get("/api/mcp")
    names = [s["name"] for s in r.json()["servers"]]
    assert "fs" in names


def test_update_server():
    client.post(
        "/api/mcp",
        json={"name": "myserver", "command": "node", "args": ["old.js"]},
    )
    r = client.patch("/api/mcp/myserver", json={"args": ["new.js"]})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Verify the update stuck
    servers = client.get("/api/mcp").json()["servers"]
    srv = next(s for s in servers if s["name"] == "myserver")
    assert srv["args"] == ["new.js"]


def test_delete_server():
    client.post("/api/mcp", json={"name": "todelete", "command": "node", "args": []})
    r = client.delete("/api/mcp/todelete")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    servers = client.get("/api/mcp").json()["servers"]
    assert not any(s["name"] == "todelete" for s in servers)


def test_delete_nonexistent():
    r = client.delete("/api/mcp/ghost")
    assert r.status_code == 404


def test_update_nonexistent():
    r = client.patch("/api/mcp/ghost", json={"command": "x"})
    assert r.status_code == 404


def test_add_empty_name():
    r = client.post("/api/mcp", json={"name": "", "command": "node"})
    assert r.status_code == 400


def test_add_empty_command():
    r = client.post("/api/mcp", json={"name": "srv", "command": ""})
    assert r.status_code == 400


def test_test_server_not_found():
    r = client.post("/api/mcp/ghost/test")
    assert r.status_code == 404


def test_config_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify config is written to disk and reloaded correctly."""
    fake = tmp_path / "cfg" / "claude_desktop_config.json"
    fake.parent.mkdir(parents=True)
    monkeypatch.setattr(mcp_mod, "_CLAUDE_CONFIG", fake)
    client.post(
        "/api/mcp",
        json={
            "name": "persist",
            "command": "uvx",
            "args": ["mcp-server-git"],
        },
    )
    raw = json.loads(fake.read_text())
    assert "persist" in raw["mcpServers"]
    assert raw["mcpServers"]["persist"]["command"] == "uvx"
