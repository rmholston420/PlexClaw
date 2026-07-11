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

def test_git_roots_returns_nearest_containing_repo(tmp_path, monkeypatch):
    import app.fs_routes as fs_routes

    root = tmp_path / "root"
    repo = root / "repo"
    nested = repo / "src" / "pkg"
    nested.mkdir(parents=True)
    (repo / ".git").mkdir()
    monkeypatch.setattr(fs_routes, "get_default_fs_root()", root.resolve())

    with TestClient(app) as local_client:
        resp = local_client.get("/api/fs/git-roots", params={"start": str(nested)})

    assert resp.status_code == 200
    data = resp.json()
    assert data["root"] == str(root.resolve())
    assert data["roots"] == [str(repo.resolve())]

