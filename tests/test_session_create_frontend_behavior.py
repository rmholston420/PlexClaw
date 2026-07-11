from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import PROTOCOL_VERSION

client = TestClient(app)


def test_session_create_response_matches_frontend_bootstrap_expectations() -> None:
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"]
    assert data["status"] == "created"
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["model"] == "claude-sonnet-4-5"
    assert data["provider"] == "cloud"
    assert data["permission_mode"] == "manual"
    assert data["cwd"] is None
    assert isinstance(data["mock_mode"], bool)

    html = Path("frontend/index.html").read_text()
    js = Path("frontend/sdk-bridge-client.js").read_text()

    assert 'id="runtime-mode-label"' in html
    assert "function setRuntimeMode(mockMode)" in js
    assert "if (data.model) state.model = data.model;" in js
    assert "if (data.provider) state.provider = data.provider;" in js
    assert (
        "if (data.permission_mode) "
        "state.permissionMode = data.permission_mode;"
    ) in js
    assert (
        "if (Object.prototype.hasOwnProperty.call(data, 'cwd')) "
        "setCwd(data.cwd);"
    ) in js
    assert "renderPermissionMode();" in js
    assert (
        "if (typeof data.mock_mode === 'boolean') "
        "setRuntimeMode(data.mock_mode);"
    ) in js


def test_session_create_defaults_match_local_frontend_bootstrap() -> None:
    response = client.post("/api/sessions", json={})

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"]
    assert data["status"] == "created"
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen3:latest"
    assert isinstance(data["mock_mode"], bool)
