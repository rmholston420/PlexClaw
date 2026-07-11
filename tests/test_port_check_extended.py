"""Extended tests for app/port_check.py.

Covers:
  - format_blocked_ports with a single blocked port (still appends summary)
  - blocked_ports with an empty iterable
  - blocked_ports with a custom iterable of ports
  - DEFAULT_PORTS constant shape
"""
from __future__ import annotations

import socket

from app import port_check
from app.port_check import DEFAULT_PORTS, blocked_ports, format_blocked_ports


class _FakeSocket:
    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail
        self.closed = False

    def bind(self, addr: tuple[str, int]) -> None:
        if self.should_fail:
            raise OSError("Address already in use")

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# DEFAULT_PORTS constant
# ---------------------------------------------------------------------------

def test_default_ports_is_tuple():
    assert isinstance(DEFAULT_PORTS, tuple)


def test_default_ports_contains_expected_entries():
    labels = {label for _, label in DEFAULT_PORTS}
    assert "backend" in labels
    assert "frontend" in labels


def test_default_ports_entries_are_int_str_tuples():
    for port, label in DEFAULT_PORTS:
        assert isinstance(port, int)
        assert isinstance(label, str)


# ---------------------------------------------------------------------------
# blocked_ports edge cases
# ---------------------------------------------------------------------------

def test_blocked_ports_empty_iterable(monkeypatch):
    def fake_socket(*args, **kwargs):
        return _FakeSocket(should_fail=False)

    monkeypatch.setattr(socket, "socket", fake_socket)
    assert blocked_ports([]) == []


def test_blocked_ports_all_blocked(monkeypatch):
    def fake_socket(*args, **kwargs):
        return _FakeSocket(should_fail=True)

    monkeypatch.setattr(socket, "socket", fake_socket)
    result = blocked_ports(((9001, "svc-a"), (9002, "svc-b")))
    assert result == [(9001, "svc-a"), (9002, "svc-b")]


def test_blocked_ports_socket_is_always_closed(monkeypatch):
    sockets_created: list[_FakeSocket] = []

    def fake_socket(*args, **kwargs):
        s = _FakeSocket(should_fail=False)
        sockets_created.append(s)
        return s

    monkeypatch.setattr(socket, "socket", fake_socket)
    blocked_ports(((8020, "a"), (5555, "b")))

    for s in sockets_created:
        assert s.closed, "Socket was not closed after check"


def test_blocked_ports_socket_is_closed_even_on_oserror(monkeypatch):
    """Sockets must be closed in the finally block even when bind raises."""
    sockets_created: list[_FakeSocket] = []

    def fake_socket(*args, **kwargs):
        s = _FakeSocket(should_fail=True)
        sockets_created.append(s)
        return s

    monkeypatch.setattr(socket, "socket", fake_socket)
    blocked_ports(((8020, "b"),))

    for s in sockets_created:
        assert s.closed


# ---------------------------------------------------------------------------
# format_blocked_ports
# ---------------------------------------------------------------------------

def test_format_blocked_ports_single_port_appends_summary():
    lines = format_blocked_ports([(8020, "backend")])
    assert lines == [
        "[run.sh] Port 8020 already in use (backend).",
        "[run.sh] Stop the existing process or free the port, then retry.",
    ]


def test_format_blocked_ports_empty_returns_empty_list():
    assert format_blocked_ports([]) == []


def test_format_blocked_ports_message_format():
    lines = format_blocked_ports([(1234, "myservice")])
    assert "1234" in lines[0]
    assert "myservice" in lines[0]


def test_format_blocked_ports_two_ports():
    lines = format_blocked_ports([(8020, "backend"), (5555, "frontend")])
    assert len(lines) == 3  # 2 port lines + 1 summary
    assert lines[-1].startswith("[run.sh] Stop")
