from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_frontend_index_html() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    expected = Path("frontend/index.html").read_text(encoding="utf-8")
    assert response.text == expected


def test_legacy_frontend_entrypoint_redirects_to_root() -> None:
    client = TestClient(app)

    response = client.get("/plexclaw-ui-canonical.html", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/"
