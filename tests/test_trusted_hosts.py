import importlib
import sys

from fastapi.testclient import TestClient


def load_app_with_hosts(monkeypatch, hosts: str):
    monkeypatch.setenv("PLEXCLAW_ALLOWED_HOSTS", hosts)
    sys.modules.pop("app.main", None)
    import app.main
    importlib.reload(app.main)
    return app.main.app


def test_trusted_hosts_allow_configured_host(monkeypatch):
    app = load_app_with_hosts(monkeypatch, "testserver,localhost,127.0.0.1")
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Host": "testserver"},
    )

    assert response.status_code == 200


def test_trusted_hosts_reject_unconfigured_host(monkeypatch):
    app = load_app_with_hosts(monkeypatch, "testserver,localhost,127.0.0.1")
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Host": "evil.example.com"},
    )

    assert response.status_code == 400
