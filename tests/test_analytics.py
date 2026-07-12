"""Tests for app/analytics_routes.py — usage analytics from event store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.event_store as es
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(es, "DB_PATH", tmp_path / "test_events.db")
    es.close_db()
    es.init_db()
    yield
    es.close_db()


def _insert_completed(
    session_id: str,
    model: str,
    inp: int,
    out: int,
    cr: int = 0,
    cw: int = 0,
) -> None:
    """Insert a synthetic assistant.completed event with usage metadata."""
    payload = {
        "model": model,
        "usage": {
            "input_tokens":       inp,
            "output_tokens":      out,
            "cache_read_tokens":  cr,
            "cache_write_tokens": cw,
        },
        "stop_reason": "end_turn",
        "text": "",
    }
    with es._db_lock:
        c = es._get_conn()
        c.execute(
            "INSERT INTO events (session_id, seq, type, payload) VALUES (?,?,?,?)",
            (session_id, 1, "assistant.completed", json.dumps(payload)),
        )
        c.commit()


# ── Totals ──────────────────────────────────────────────────────────────────

def test_analytics_empty():
    r = client.get("/api/analytics")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["input_tokens"] == 0
    assert data["totals"]["cost_usd"] == 0.0
    assert data["by_model"] == {}
    assert data["daily_series"] == []


def test_analytics_single_event():
    _insert_completed("sess1", "claude-sonnet-4", inp=1000, out=200)
    r = client.get("/api/analytics")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["input_tokens"] == 1000
    assert data["totals"]["output_tokens"] == 200
    assert data["totals"]["calls"] == 1
    # Cost should be non-zero for a cloud model
    assert data["totals"]["cost_usd"] > 0


def test_analytics_by_model():
    _insert_completed("s1", "claude-sonnet-4", inp=500, out=100)
    _insert_completed("s2", "claude-opus-4", inp=200, out=50)
    r = client.get("/api/analytics")
    data = r.json()
    assert "claude-sonnet-4" in data["by_model"]
    assert "claude-opus-4" in data["by_model"]


def test_analytics_local_model_zero_cost():
    _insert_completed("s1", "qwen3-coder:latest", inp=10000, out=5000)
    r = client.get("/api/analytics")
    data = r.json()
    # Local model should have zero cost regardless of token count
    by_model = data["by_model"]
    for model_name, stats in by_model.items():
        if "qwen" in model_name.lower():
            assert stats["cost_usd"] == 0.0


# ── Per-session ──────────────────────────────────────────────────────────────

def test_session_analytics():
    _insert_completed("session-abc", "claude-haiku-4", inp=300, out=100)
    r = client.get("/api/analytics/session/session-abc")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "session-abc"
    assert data["input_tokens"] == 300
    assert data["output_tokens"] == 100


def test_session_analytics_missing():
    r = client.get("/api/analytics/session/does-not-exist")
    assert r.status_code == 200
    data = r.json()
    assert data["input_tokens"] == 0
    assert data["calls"] == 0


# ── Model breakdown ──────────────────────────────────────────────────────────

def test_model_breakdown_route():
    _insert_completed("s", "claude-haiku-4", inp=100, out=50)
    r = client.get("/api/analytics/models")
    assert r.status_code == 200
    assert "by_model" in r.json()


# ── Daily series ─────────────────────────────────────────────────────────────

def test_daily_series_route():
    _insert_completed("s", "claude-sonnet-4", inp=100, out=50)
    r = client.get("/api/analytics/daily?days=7")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
