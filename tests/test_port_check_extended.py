from __future__ import annotations

import socket

from app.port_check import DEFAULT_PORTS, blocked_ports, format_blocked_ports


def test_default_ports_shape():
    assert isinstance(DEFAULT_PORTS, tuple)
    assert DEFAULT_PORTS == (
        (8020, "plexclaw"),
    )
    assert all(
        isinstance(item, tuple) and len(item) == 2 for item in DEFAULT_PORTS
    )
    assert all(
        isinstance(port, int) and isinstance(name, str)
        for port, name in DEFAULT_PORTS
    )


def test_blocked_ports_empty_iterable():
    assert blocked_ports([]) == []


def test_blocked_ports_all_blocked(monkeypatch):
    class BusySocket:
        def bind(self, addr):
            raise OSError("in use")

        def close(self):
            return None

    monkeypatch.setattr(socket, "socket", lambda *a, **k: BusySocket())
    result = blocked_ports([(8000, "a"), (8001, "b")])
    assert result == [(8000, "a"), (8001, "b")]


def test_blocked_ports_closes_socket_on_bind_error(monkeypatch):
    class BusySocket:
        def __init__(self):
            self.closed = False

        def bind(self, addr):
            raise OSError("in use")

        def close(self):
            self.closed = True

    sockets = []

    def factory(*args, **kwargs):
        s = BusySocket()
        sockets.append(s)
        return s

    monkeypatch.setattr(socket, "socket", factory)
    blocked_ports([(8000, "backend")])

    assert len(sockets) == 1
    assert sockets[0].closed is True


def test_format_blocked_ports_single_port_has_retry_line():
    msg = format_blocked_ports([(8000, "backend")])
    assert isinstance(msg, list)
    assert any("8000" in line for line in msg)
    assert any("backend" in line for line in msg)
    assert any("retry" in line.lower() for line in msg)
