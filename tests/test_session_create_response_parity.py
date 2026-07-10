from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_session_response_includes_provider_and_tool_search_metadata():
    response = client.post(
        "/api/sessions",
        json={
            "model": "claude-sonnet-4-5",
            "provider": "ollama",
            "tool_search_mode": "false",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["provider"] == "ollama"
    assert data["provider_base_url"] == "http://127.0.0.1:11434"
    assert data["tool_search_mode"] == "false"
    assert data["tool_search_active"] is True
