"""Unit tests for app/websocket_manager.WebSocketManager.

Uses a lightweight AsyncMock WebSocket stub so we don't need a running
ASGI server. Covers:
  - add() / remove() / connection_count() / session_count()
  - broadcast() fan-out to multiple connections
  - broadcast() removes dead connections (send_text raises)
  - broadcast() to a session with no connections is a no-op
  - remove() on non-existent session is a no-op
  - ws_manager singleton is exported
"""
from __future__ import annotations

import pytest

from app.websocket_manager import WebSocketManager
from app.schemas import WSEnvelope


# ---------------------------------------------------------------------------
# Minimal WebSocket stub
# ---------------------------------------------------------------------------


class _FakeWS:
    """Minimal async stand-in for fastapi.WebSocket."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.sent: list[str] = []

    async def send_text(self, data: str) -> None:
        if self._fail:
            raise RuntimeError("connection closed")
        self.sent.append(data)


def _env(session_id: str = "s1", seq: int = 1) -> WSEnvelope:
    return WSEnvelope(
        type="assistant.delta",
        session_id=session_id,
        seq=seq,
        payload={"text": "hi"},
    )


# ---------------------------------------------------------------------------
# add / remove / counts
# ---------------------------------------------------------------------------


def test_add_increments_connection_count():
    mgr = WebSocketManager()
    ws = _FakeWS()
    assert mgr.connection_count("s1") == 0
    mgr.add("s1", ws)
    assert mgr.connection_count("s1") == 1


def test_add_multiple_connections_same_session():
    mgr = WebSocketManager()
    ws1, ws2 = _FakeWS(), _FakeWS()
    mgr.add("s1", ws1)
    mgr.add("s1", ws2)
    assert mgr.connection_count("s1") == 2


def test_remove_decrements_connection_count():
    mgr = WebSocketManager()
    ws = _FakeWS()
    mgr.add("s1", ws)
    mgr.remove("s1", ws)
    assert mgr.connection_count("s1") == 0


def test_remove_last_connection_purges_session_key():
    mgr = WebSocketManager()
    ws = _FakeWS()
    mgr.add("s1", ws)
    mgr.remove("s1", ws)
    # session key must be gone so session_count is 0
    assert mgr.session_count() == 0


def test_remove_nonexistent_session_is_noop():
    mgr = WebSocketManager()
    ws = _FakeWS()
    mgr.remove("ghost", ws)  # must not raise


def test_remove_ws_not_in_list_is_noop():
    mgr = WebSocketManager()
    ws_a, ws_b = _FakeWS(), _FakeWS()
    mgr.add("s1", ws_a)
    mgr.remove("s1", ws_b)  # ws_b was never added
    assert mgr.connection_count("s1") == 1


def test_session_count_multiple_sessions():
    mgr = WebSocketManager()
    mgr.add("s1", _FakeWS())
    mgr.add("s2", _FakeWS())
    assert mgr.session_count() == 2


def test_connection_count_unknown_session_returns_zero():
    mgr = WebSocketManager()
    assert mgr.connection_count("no-such-session") == 0


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_delivers_to_all_connections():
    mgr = WebSocketManager()
    ws1, ws2 = _FakeWS(), _FakeWS()
    mgr.add("s1", ws1)
    mgr.add("s1", ws2)
    env = _env("s1")
    await mgr.broadcast(env)
    expected = env.model_dump_json()
    assert ws1.sent == [expected]
    assert ws2.sent == [expected]


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connection():
    mgr = WebSocketManager()
    good = _FakeWS()
    dead = _FakeWS(fail=True)
    mgr.add("s1", good)
    mgr.add("s1", dead)
    assert mgr.connection_count("s1") == 2

    await mgr.broadcast(_env("s1"))

    # dead socket must be evicted
    assert mgr.connection_count("s1") == 1
    assert len(good.sent) == 1


@pytest.mark.asyncio
async def test_broadcast_all_dead_removes_session():
    mgr = WebSocketManager()
    dead = _FakeWS(fail=True)
    mgr.add("s1", dead)
    await mgr.broadcast(_env("s1"))
    assert mgr.session_count() == 0


@pytest.mark.asyncio
async def test_broadcast_no_connections_is_noop():
    mgr = WebSocketManager()
    await mgr.broadcast(_env("empty-session"))  # must not raise


@pytest.mark.asyncio
async def test_broadcast_only_targets_correct_session():
    mgr = WebSocketManager()
    ws_a = _FakeWS()
    ws_b = _FakeWS()
    mgr.add("a", ws_a)
    mgr.add("b", ws_b)
    await mgr.broadcast(_env("a", seq=99))
    assert len(ws_a.sent) == 1
    assert len(ws_b.sent) == 0


# ---------------------------------------------------------------------------
# singleton
# ---------------------------------------------------------------------------


def test_ws_manager_singleton_is_websocket_manager():
    from app.websocket_manager import ws_manager
    assert isinstance(ws_manager, WebSocketManager)
