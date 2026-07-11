from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_update_session_maps_keyerror_to_404(monkeypatch):
    async def fake_update_session(session_id: str, permission_mode=None):
        raise KeyError("missing-session")

    monkeypatch.setattr(main.runtime, "update_session", fake_update_session)

    res = client.patch("/api/sessions/missing", json={"permission_mode": "manual"})
    assert res.status_code == 404
    assert "missing-session" in res.json()["detail"]


def test_update_session_maps_valueerror_to_400(monkeypatch):
    async def fake_update_session(session_id: str, permission_mode=None):
        raise ValueError("bad permission mode")

    monkeypatch.setattr(main.runtime, "update_session", fake_update_session)

    res = client.patch("/api/sessions/s1", json={"permission_mode": "manual"})
    assert res.status_code == 400
    assert "bad permission mode" in res.json()["detail"]


def test_interrupt_session_maps_keyerror_to_404(monkeypatch):
    async def fake_interrupt_session(session_id: str):
        raise KeyError("no such session")

    monkeypatch.setattr(main.runtime, "interrupt_session", fake_interrupt_session)

    res = client.post("/api/sessions/missing/interrupt")
    assert res.status_code == 404
    assert "no such session" in res.json()["detail"]


def test_delete_session_maps_keyerror_to_404(monkeypatch):
    async def fake_delete_session(session_id: str):
        raise KeyError("gone")

    monkeypatch.setattr(main.runtime, "delete_session", fake_delete_session)

    res = client.delete("/api/sessions/missing")
    assert res.status_code == 404
    assert "gone" in res.json()["detail"]


def test_upload_context_file_rejects_oversize():
    res = client.post(
        "/api/sessions/s1/context",
        files={"file": ("big.txt", b"x" * (200 * 1024 + 1), "text/plain")},
    )
    assert res.status_code == 413
    assert "200KB" in res.json()["detail"]


def test_upload_context_file_rejects_non_utf8():
    res = client.post(
        "/api/sessions/s1/context",
        files={"file": ("bad.bin", b"\xff\xfe\xfa", "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "UTF-8" in res.json()["detail"]


def test_upload_context_file_maps_keyerror_to_404(monkeypatch):
    def fake_add_context_file(session_id: str, filename: str, text: str):
        raise KeyError("missing live session")

    monkeypatch.setattr(main.runtime, "add_context_file", fake_add_context_file)

    res = client.post(
        "/api/sessions/missing/context",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 404
    assert "missing live session" in res.json()["detail"]


def test_list_context_maps_keyerror_to_404(monkeypatch):
    def fake_list_context_files(session_id: str):
        raise KeyError("missing context owner")

    monkeypatch.setattr(main.runtime, "list_context_files", fake_list_context_files)

    res = client.get("/api/sessions/missing/context")
    assert res.status_code == 404
    assert "missing context owner" in res.json()["detail"]


def test_delete_context_file_maps_keyerror_to_404(monkeypatch):
    def fake_remove_context_file(session_id: str, filename: str):
        raise KeyError("missing file owner")

    monkeypatch.setattr(
        main.runtime,
        "remove_context_file",
        fake_remove_context_file,
    )

    res = client.delete("/api/sessions/missing/context/note.txt")
    assert res.status_code == 404
    assert "missing file owner" in res.json()["detail"]


def test_get_providers_returns_expected_shape(monkeypatch):
    async def fake_fetch_ollama_models():
        return ["phi3", "llama3"]

    async def fake_fetch_vllm_models():
        return ["meta-1"]

    monkeypatch.setattr(main, "_fetch_ollama_models", fake_fetch_ollama_models)
    monkeypatch.setattr(main, "_fetch_vllm_models", fake_fetch_vllm_models)
    monkeypatch.setattr(main, "get_ollama_base_url", lambda: "http://ollama.local")
    monkeypatch.setattr(main, "get_vllm_base_url", lambda: "http://vllm.local")
    monkeypatch.setattr(main, "get_cloud_models", lambda: ["claude-x", "gpt-y"])

    res = client.get("/api/providers")
    assert res.status_code == 200
    data = res.json()

    assert data["default_provider"] == "cloud"
    assert data["providers"]["cloud"]["models"] == ["claude-x", "gpt-y"]
    assert data["providers"]["ollama"]["base_url"] == "http://ollama.local"
    assert data["providers"]["ollama"]["models"] == ["phi3", "llama3"]
    assert data["providers"]["vllm"]["base_url"] == "http://vllm.local"
    assert data["providers"]["vllm"]["models"] == ["meta-1"]


def test_get_provider_health_reflects_fetch_results(monkeypatch):
    async def fake_fetch_ollama_models():
        return ["phi3"]

    async def fake_fetch_vllm_models():
        return []

    monkeypatch.setattr(main, "_fetch_ollama_models", fake_fetch_ollama_models)
    monkeypatch.setattr(main, "_fetch_vllm_models", fake_fetch_vllm_models)

    res = client.get("/api/providers/health")
    assert res.status_code == 200
    data = res.json()

    assert data["cloud"] == {"ok": True}
    assert data["ollama"] == {"ok": True, "models": 1}
    assert data["vllm"] == {"ok": False, "models": 0}


def test_archive_rename_calls_runtime(monkeypatch):
    seen = {}

    async def fake_rename_archive_session(session_id: str, title: str):
        seen["session_id"] = session_id
        seen["title"] = title

    monkeypatch.setattr(
        main.runtime,
        "rename_archive_session",
        fake_rename_archive_session,
    )

    res = client.post("/api/archive/sessions/a1/rename", json={"title": "Renamed"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert seen == {"session_id": "a1", "title": "Renamed"}


def test_archive_tag_calls_runtime_with_none(monkeypatch):
    seen = {}

    async def fake_tag_archive_session(session_id: str, tag):
        seen["session_id"] = session_id
        seen["tag"] = tag

    monkeypatch.setattr(
        main.runtime,
        "tag_archive_session",
        fake_tag_archive_session,
    )

    res = client.post("/api/archive/sessions/a1/tag", json={"tag": None})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert seen == {"session_id": "a1", "tag": None}


def test_archive_tag_calls_runtime_with_value(monkeypatch):
    seen = {}

    async def fake_tag_archive_session(session_id: str, tag):
        seen["session_id"] = session_id
        seen["tag"] = tag

    monkeypatch.setattr(
        main.runtime,
        "tag_archive_session",
        fake_tag_archive_session,
    )

    res = client.post("/api/archive/sessions/a2/tag", json={"tag": "keep"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    assert seen == {"session_id": "a2", "tag": "keep"}
