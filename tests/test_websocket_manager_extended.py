"""Extended tests for app/websocket_manager.py.

Covers:
  - session_count with multiple sessions
  - connection_count after removals
  - remove on session that does not exist is a no-op
  - remove last connection cleans up the session key
  - broadcast to empty session set is a no-op
  - broadcast removes dead sockets silently
  - ws_manager singleton is a WebSocketManager instance
"""
from __future__ import annotations

import pytest

from app.websocket_manager import WebSocketManager, ws_manager
from app.schemas import WSEnvelope
from app.normalizer import normalize_text_delta


class _FakeWS:
    """Minimal WebSocket stand-in."""

    def __init__(self, fail: bool = False) -> None:
        self.sent: list[str] = []
        self.fail = fail

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("dead socket")
        self.sent.append(data)


@pytest.fixture()
def mgr() -> WebSocketManager:
    return WebSocketManager()


# ---------------------------------------------------------------------------
# session_count
# ---------------------------------------------------------------------------

def test_session_count_zero_initially(mgr):
    assert mgr.session_count() == 0


def test_session_count_increments(mgr):
    mgr.add("s1", _FakeWS())
    assert mgr.session_count() == 1
    mgr.add("s2", _FakeWS())
    assert mgr.session_count() == 2


def test_session_count_same_session_not_double_counted(mgr):
    ws1 = _FakeWS()
    ws2 = _FakeWS()
    mgr.add("s1", ws1)
    mgr.add("s1", ws2)
    assert mgr.session_count() == 1


def test_session_count_decrements_when_last_conn_removed(mgr):
    ws = _FakeWS()
    mgr.add("s1", ws)
    mgr.remove("s1", ws)
    assert mgr.session_count() == 0


# ---------------------------------------------------------------------------
# connection_count
# ---------------------------------------------------------------------------

def test_connection_count_zero_for_unknown_session(mgr):
    assert mgr.connection_count("ghost") == 0


def test_connection_count_multiple_connections(mgr):
    mgr.add("s1", _FakeWS())
    mgr.add("s1", _FakeWS())
    mgr.add("s1", _FakeWS())
    assert mgr.connection_count("s1") == 3


# ---------------------------------------------------------------------------
# remove edge cases
# ---------------------------------------------------------------------------

def test_remove_unknown_session_is_noop(mgr):
    mgr.remove("nonexistent", _FakeWS())  # must not raise


def test_remove_ws_not_in_session_is_noop(mgr):
    ws_a = _FakeWS()
    ws_b = _FakeWS()
    mgr.add("s1", ws_a)
    mgr.remove("s1", ws_b)  # ws_b was never added — must not raise
    assert mgr.connection_count("s1") == 1


def test_remove_last_connection_purges_session_key(mgr):
    ws = _FakeWS()
    mgr.add("s1", ws)
    mgr.remove("s1", ws)
    # Session key should be gone — session_count back to 0
    assert mgr.session_count() == 0
    assert mgr.connection_count("s1") == 0


# ---------------------------------------------------------------------------
# broadcast
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_broadcast_sends_to_all_connections(mgr):
    ws1 = _FakeWS()
    ws2 = _FakeWS()
    mgr.add("s1", ws1)
    mgr.add("s1", ws2)
    envelope = normalize_text_delta("s1", 0, "hello")
    await mgr.broadcast(envelope)
    assert len(ws1.sent) == 1
    assert len(ws2.sent) == 1
    assert ws1.sent[0] == ws2.sent[0]  # same JSON payload


@pytest.mark.asyncio
async def test_broadcast_to_empty_session_is_noop(mgr):
    envelope = normalize_text_delta("ghost", 0, "hello")
    await mgr.broadcast(envelope)  # must not raise


@pytest.mark.asyncio
async def test_broadcast_removes_dead_sockets(mgr):
    good = _FakeWS(fail=False)
    dead = _FakeWS(fail=True)
    mgr.add("s1", good)
    mgr.add("s1", dead)
    assert mgr.connection_count("s1") == 2

    envelope = normalize_text_delta("s1", 0, "ping")
    await mgr.broadcast(envelope)  # dead socket raises internally

    assert mgr.connection_count("s1") == 1
    assert len(good.sent) == 1


@pytest.mark.asyncio
async def test_broadcast_all_dead_cleans_session(mgr):
    dead = _FakeWS(fail=True)
    mgr.add("s1", dead)
    envelope = normalize_text_delta("s1", 0, "ping")
    await mgr.broadcast(envelope)
    assert mgr.session_count() == 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def test_ws_manager_singleton_is_websocket_manager():
    assert isinstance(ws_manager, WebSocketManager)
