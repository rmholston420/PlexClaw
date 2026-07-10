from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_cloud_models_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("PLEXCLAW_CLOUD_MODELS", raising=False)
    client = TestClient(app)

    resp = client.get("/api/providers")
    assert resp.status_code == 200

    data = resp.json()
    assert data["providers"]["cloud"]["models"] == [
        "claude-sonnet-4-5",
        "claude-opus-4-5",
        "claude-haiku-4-5",
    ]


def test_cloud_models_env_override(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_CLOUD_MODELS",
        "claude-opus-4, claude-sonnet-4-5, claude-3-5-sonnet",
    )
    client = TestClient(app)

    resp = client.get("/api/providers")
    assert resp.status_code == 200

    data = resp.json()
    assert data["providers"]["cloud"]["models"] == [
        "claude-opus-4",
        "claude-sonnet-4-5",
        "claude-3-5-sonnet",
    ]


def test_cloud_models_env_override_ignores_empty_entries(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_CLOUD_MODELS",
        " , claude-opus-4 , , claude-sonnet-4-5 , ",
    )
    client = TestClient(app)

    resp = client.get("/api/providers")
    assert resp.status_code == 200

    data = resp.json()
    assert data["providers"]["cloud"]["models"] == [
        "claude-opus-4",
        "claude-sonnet-4-5",
    ]
