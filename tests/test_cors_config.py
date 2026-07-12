import importlib
import sys

from fastapi.testclient import TestClient


def load_app_with_origins(monkeypatch, origins: str):
    monkeypatch.setenv("PLEXCLAW_ALLOWED_ORIGINS", origins)
    sys.modules.pop("app.main", None)
    import app.main
    importlib.reload(app.main)
    return app.main.app


def test_cors_respects_env_allowed_origins(monkeypatch):
    app = load_app_with_origins(
        monkeypatch,
        "http://frontend.local,http://localhost:8020",
    )
    client = TestClient(app)

    origin = "http://frontend.local"
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in (200, 400)
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_does_not_reflect_disallowed_origin(monkeypatch):
    app = load_app_with_origins(
        monkeypatch,
        "http://frontend.local",
    )
    client = TestClient(app)

    origin = "http://not-allowed.local"
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != origin
