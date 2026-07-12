from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.schemas import PROTOCOL_VERSION


def _coro(val):
    async def _inner():
        return val
    return _inner()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_session_value_error_maps_to_400(monkeypatch):
    async def boom(req):
        raise ValueError("bad create")

    monkeypatch.setattr(main.runtime, "create_session", boom)

    req = main.SessionCreateRequest(
        model="claude-sonnet-4-5",
        provider="cloud",
        permission_mode="manual",
    )

    with pytest.raises(main.HTTPException) as exc:
        await main.create_session(req)

    assert exc.value.status_code == 400
    assert exc.value.detail == "bad create"


@pytest.mark.asyncio
async def test_update_session_key_error_maps_to_404(monkeypatch):
    async def boom(*args, **kwargs):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "update_session", boom)

    req = main.SessionUpdateRequest(permission_mode="manual")

    with pytest.raises(main.HTTPException) as exc:
        await main.update_session("nope", req)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_session_value_error_maps_to_400(monkeypatch):
    async def boom(*args, **kwargs):
        raise ValueError("bad update")

    monkeypatch.setattr(main.runtime, "update_session", boom)

    req = main.SessionUpdateRequest(permission_mode="manual")

    with pytest.raises(main.HTTPException) as exc:
        await main.update_session("s1", req)

    assert exc.value.status_code == 400
    assert exc.value.detail == "bad update"


@pytest.mark.asyncio
async def test_interrupt_session_key_error_maps_to_404(monkeypatch):
    async def boom(session_id):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "interrupt_session", boom)

    with pytest.raises(main.HTTPException) as exc:
        await main.interrupt_session("nope")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_key_error_maps_to_404(monkeypatch):
    async def boom(session_id):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "delete_session", boom)

    with pytest.raises(main.HTTPException) as exc:
        await main.delete_session("nope")

    assert exc.value.status_code == 404


def test_upload_context_file_too_large_returns_413(client):
    response = client.post(
        "/api/sessions/s1/context",
        files={"file": ("big.txt", b"a" * (200 * 1024 + 1), "text/plain")},
    )
    assert response.status_code == 413
    assert "200KB" in response.json()["detail"]


def test_upload_context_file_non_utf8_returns_400(client, monkeypatch):
    monkeypatch.setattr(main.runtime, "add_context_file", lambda *args, **kwargs: None)

    response = client.post(
        "/api/sessions/s1/context",
        files={"file": ("bin.txt", b"\xff\xfe\xfd", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "UTF-8" in response.json()["detail"]


def test_upload_context_file_runtime_value_error_returns_400(client, monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("bad file")

    monkeypatch.setattr(main.runtime, "add_context_file", boom)

    response = client.post(
        "/api/sessions/s1/context",
        files={"file": ("ok.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "bad file"


def test_upload_context_file_runtime_key_error_returns_404(client, monkeypatch):
    def boom(*args, **kwargs):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "add_context_file", boom)

    response = client.post(
        "/api/sessions/s1/context",
        files={"file": ("ok.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_context_key_error_maps_to_404(monkeypatch):
    def boom(session_id):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "list_context_files", boom)

    with pytest.raises(main.HTTPException) as exc:
        await main.list_context("nope")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_context_file_key_error_maps_to_404(monkeypatch):
    def boom(*args, **kwargs):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "remove_context_file", boom)

    with pytest.raises(main.HTTPException) as exc:
        await main.delete_context_file("s1", "gone.txt")

    assert exc.value.status_code == 404


def test_get_cloud_models_uses_default_when_env_blank(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_CLOUD_MODELS", "")
    assert main.get_cloud_models() == main.DEFAULT_CLOUD_MODELS


def test_get_cloud_models_strips_and_filters_env(monkeypatch):
    monkeypatch.setenv("PLEXCLAW_CLOUD_MODELS", "  a , , b ,, c  ")
    assert main.get_cloud_models() == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_fetch_ollama_models_success(monkeypatch):
    monkeypatch.setattr(main, "get_ollama_base_url", lambda: "http://ollama.test")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"models": [{"name": "m1"}, {"name": "m2"}, {"x": "skip"}]}
            ).encode("utf-8")

    monkeypatch.setattr(
        main.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    models = await main._fetch_ollama_models()
    assert models == ["m1", "m2"]


@pytest.mark.asyncio
async def test_fetch_ollama_models_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(main, "get_ollama_base_url", lambda: "http://ollama.test")
    monkeypatch.setattr(
        main.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    models = await main._fetch_ollama_models()
    assert models == []


@pytest.mark.asyncio
async def test_fetch_vllm_models_success(monkeypatch):
    monkeypatch.setattr(main, "get_vllm_base_url", lambda: "http://vllm.test")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {"data": [{"id": "x"}, {"id": "y"}, {"name": "skip"}]}
            ).encode("utf-8")

    monkeypatch.setattr(
        main.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    models = await main._fetch_vllm_models()
    assert models == ["x", "y"]


@pytest.mark.asyncio
async def test_fetch_vllm_models_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(main, "get_vllm_base_url", lambda: "http://vllm.test")
    monkeypatch.setattr(
        main.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    models = await main._fetch_vllm_models()
    assert models == []


def test_render_session_markdown_covers_all_rendered_sections():
    events = [
        {"type": "assistant.delta", "payload": {"text": "hello "}},
        {"type": "assistant.delta", "payload": {"text": "world"}},
        {"type": "system.message", "payload": {"text": "system ready"}},
        {
            "type": "tool.delta",
            "payload": {"tool_id": "t1", "tool_input": {"cmd": "ls -la"}},
        },
        {
            "type": "tool.started",
            "payload": {
                "tool_id": "t1",
                "tool_name": "bash",
                "tool_input": {"cmd": "wrong"},
            },
        },
        {
            "type": "tool.completed",
            "payload": {"tool_name": "bash", "output": "done"},
        },
        {
            "type": "tool.permission_required",
            "payload": {"tool_name": "rm", "tool_input": {"path": "/tmp/x"}},
        },
        {
            "type": "tool.permission_decided",
            "payload": {"tool_name": "rm", "decision": "approved"},
        },
        {"type": "session.failed", "payload": {"error": "boom"}},
    ]

    out = main._render_session_markdown("sess1", events)

    assert "# Session sess1" in out
    assert "## Assistant" in out
    assert "hello world" in out
    assert "## System" in out
    assert "system ready" in out
    assert "## Tool: bash" in out
    assert '"cmd": "ls -la"' in out
    assert "## Tool Output: bash" in out
    assert "done" in out
    assert "## Tool Approval Required: rm" in out
    assert "## Tool Approval Decision: rm" in out
    assert "approved" in out
    assert "## Error" in out
    assert "boom" in out


def test_render_session_markdown_ignores_empty_assistant_flush():
    out = main._render_session_markdown(
        "sess2",
        [{"type": "system.message", "payload": {"text": "only system"}}],
    )
    assert "## Assistant" not in out
    assert "## System" in out


def test_export_session_markdown_route(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "query_events",
        lambda session_id: _coro([{"type": "assistant.delta", "payload": {"text": "hi"}}]),
    )

    response = client.get("/api/sessions/s1/export?format=md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# Session s1" in response.text


def test_archive_endpoints(client, monkeypatch):
    async def list_sessions():
        return [{"id": "a1"}]

    async def get_session(session_id):
        return {"id": session_id}

    async def get_messages(session_id):
        return [{"msg": 1}]

    async def get_replay(session_id):
        return [{"evt": 1}]

    async def rename(session_id, title):
        return None

    async def tag(session_id, tag):
        return None

    monkeypatch.setattr(main.runtime, "list_archive_sessions", list_sessions)
    monkeypatch.setattr(main.runtime, "get_archive_session", get_session)
    monkeypatch.setattr(main.runtime, "get_archive_messages", get_messages)
    monkeypatch.setattr(main.runtime, "get_archive_replay_events", get_replay)
    monkeypatch.setattr(main.runtime, "rename_archive_session", rename)
    monkeypatch.setattr(main.runtime, "tag_archive_session", tag)
    monkeypatch.setattr(
        main,
        "normalize_session_list",
        lambda raw: [{"ok": raw[0]["id"]}],
    )
    monkeypatch.setattr(main, "normalize_session", lambda raw: {"ok": raw["id"]})

    assert client.get("/api/archive/sessions").json() == [{"ok": "a1"}]
    assert client.get("/api/archive/sessions/abc").json() == {"ok": "abc"}
    assert client.get("/api/archive/sessions/abc/messages").json() == [{"msg": 1}]
    assert client.get("/api/archive/sessions/abc/replay").json() == [{"evt": 1}]
    assert (
        client.post(
            "/api/archive/sessions/abc/rename",
            json={"title": "Renamed"},
        ).json()
        == {"ok": True}
    )
    assert (
        client.post(
            "/api/archive/sessions/abc/tag",
            json={"tag": "green"},
        ).json()
        == {"ok": True}
    )


def test_websocket_invalid_json_and_missing_pending_tool_errors(monkeypatch):
    session = SimpleNamespace(
        id="ws-errors",
        model="claude-sonnet-4-5",
        mock_mode=True,
        status="idle",
        permission_mode="manual",
        cwd=None,
        tag=None,
        title=None,
        last_activity_at=0.0,
        _seq=0,
    )

    def next_seq():
        session._seq += 1
        return session._seq

    session.next_seq = next_seq

    monkeypatch.setattr(main.runtime, "get_session", lambda session_id: session)
    monkeypatch.setattr(main.runtime, "touch_session", lambda s: None)

    async def fake_emit(_session, env):
        return None

    async def approve(*args, **kwargs):
        raise KeyError("missing")

    async def reject(*args, **kwargs):
        raise KeyError("missing")

    monkeypatch.setattr(main.runtime, "_emit", fake_emit)
    monkeypatch.setattr(main.runtime, "approve_tool_call", approve)
    monkeypatch.setattr(main.runtime, "reject_tool_call", reject)

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/ws/{session.id}?protocol_version={PROTOCOL_VERSION}"
        ) as ws:
            ws.send_text("{not json")
            err = ws.receive_json()
            assert err == {"type": "error", "detail": "invalid JSON"}

            ws.send_json({"type": "approve", "tool_id": "t1"})
            err = ws.receive_json()
            assert err == {"type": "error", "detail": "no pending tool t1"}

            ws.send_json({"type": "reject", "tool_id": "t2"})
            err = ws.receive_json()
            assert err == {"type": "error", "detail": "no pending tool t2"}
