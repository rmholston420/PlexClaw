from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import runtime_sdk as runtime
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def force_sdk_available():
    old_available = runtime._SDK_AVAILABLE
    runtime._SDK_AVAILABLE = True
    yield
    runtime._SDK_AVAILABLE = old_available


def test_create_session_rejects_invalid_provider(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "bogus",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 422


def test_create_session_rejects_invalid_permission_mode(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "cloud",
            "permission_mode": "dangerous",
        },
    )

    assert response.status_code == 422


def test_create_session_rejects_blank_model(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "   ",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 422


def test_create_session_accepts_trimmed_model(client):
    response = client.post(
        "/api/sessions",
        json={
            "model": "  claude-sonnet-4-5  ",
            "provider": "cloud",
            "permission_mode": "manual",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "created"
    assert "session_id" in body
    assert "mock_mode" in body
    assert isinstance(body["mock_mode"], bool)
    assert body["model"] == "claude-sonnet-4-5"
    assert body["provider"] == "cloud"
