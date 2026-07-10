from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_browse_root_ok():
    resp = client.get("/api/fs/browse")
    assert resp.status_code == 200
    data = resp.json()
    assert "path" in data
    assert isinstance(data["entries"], list)


def test_browse_invalid_path():
    resp = client.get("/api/fs/browse", params={"path": "/this/path/should/not/exist"})
    assert resp.status_code == 400


def test_git_roots_ok():
    resp = client.get("/api/fs/git-roots")
    assert resp.status_code == 200
    data = resp.json()
    assert "roots" in data
    assert isinstance(data["roots"], list)
