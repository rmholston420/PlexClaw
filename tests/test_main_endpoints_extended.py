from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_interrupt_session_returns_ok(monkeypatch):
    async def fake_interrupt_session(session_id):
        return None

    monkeypatch.setattr(main.runtime, "interrupt_session", fake_interrupt_session)

    resp = client.post("/api/sessions/s1/interrupt")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_upload_context_file_returns_ok_payload(monkeypatch):
    monkeypatch.setattr(
        main.runtime,
        "add_context_file",
        lambda session_id, filename, text: {"filename": filename, "size": len(text)},
    )
    monkeypatch.setattr(
        main.runtime,
        "list_context_files",
        lambda session_id: [{"filename": "note.txt", "size": 5}],
    )

    resp = client.post(
        "/api/sessions/s1/context",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "file": {"filename": "note.txt", "size": 5},
        "files": [{"filename": "note.txt", "size": 5}],
    }


def test_delete_context_file_returns_ok_payload(monkeypatch):
    monkeypatch.setattr(
        main.runtime,
        "remove_context_file",
        lambda session_id, filename: None,
    )
    monkeypatch.setattr(
        main.runtime,
        "list_context_files",
        lambda session_id: [{"filename": "note.txt", "size": 5}],
    )

    resp = client.delete("/api/sessions/s1/context/note.txt")

    assert resp.status_code == 200
    assert resp.json() == {
        "ok": True,
        "files": [{"filename": "note.txt", "size": 5}],
    }


def test_search_api_returns_search_events(monkeypatch):
    monkeypatch.setattr(main, "search_events", lambda q: [{"q": q}])

    resp = client.get("/api/search", params={"q": "needle"})

    assert resp.status_code == 200
    assert resp.json() == [{"q": "needle"}]


def test_export_session_json_returns_jsonresponse(monkeypatch):
    monkeypatch.setattr(main, "query_events", lambda session_id: [{"seq": 1}])

    resp = client.get("/api/sessions/s1/export", params={"format": "json"})

    assert resp.status_code == 200
    assert resp.json() == {"session_id": "s1", "events": [{"seq": 1}]}


def test_export_session_md_returns_markdown(monkeypatch):
    monkeypatch.setattr(main, "query_events", lambda session_id: [{"seq": 1}])
    monkeypatch.setattr(
        main,
        "_render_session_markdown",
        lambda session_id, events: "# Title",
    )

    resp = client.get("/api/sessions/s1/export", params={"format": "md"})

    assert resp.status_code == 200
    assert resp.text == "# Title"
    assert resp.headers["content-type"].startswith("text/markdown")


def test_get_events_passes_filters(monkeypatch):
    captured = {}

    def fake_query_events(session_id, event_type=None, since_seq=None):
        captured["args"] = (session_id, event_type, since_seq)
        return [{"seq": 2}]

    monkeypatch.setattr(main, "query_events", fake_query_events)

    resp = client.get(
        "/api/sessions/s1/events",
        params={"event_type": "tool.completed", "since_seq": 9},
    )

    assert resp.status_code == 200
    assert resp.json() == [{"seq": 2}]
    assert captured["args"] == ("s1", "tool.completed", 9)
