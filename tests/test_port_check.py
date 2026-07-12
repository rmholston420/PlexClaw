from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

from app import port_check


class _FakeSocket:
    def __init__(self, should_fail: bool) -> None:
        self.should_fail = should_fail
        self.closed = False
        self.sockopts: list[tuple[int, int, int]] = []

    def setsockopt(self, level: int, optname: int, value: int) -> None:
        self.sockopts.append((level, optname, value))

    def bind(self, addr: tuple[str, int]) -> None:
        if self.should_fail:
            raise OSError("Address already in use")

    def close(self) -> None:
        self.closed = True


def test_blocked_ports_returns_empty_when_all_ports_are_free(monkeypatch) -> None:
    def fake_socket(*args, **kwargs):
        return _FakeSocket(should_fail=False)

    monkeypatch.setattr(socket, "socket", fake_socket)

    assert port_check.blocked_ports(((8020, "plexclaw"),)) == []


def test_blocked_ports_reports_occupied_ports(monkeypatch) -> None:
    def fake_socket(*args, **kwargs):
        return _FakeSocket(should_fail=True)

    monkeypatch.setattr(socket, "socket", fake_socket)

    assert port_check.blocked_ports(((8020, "plexclaw"),)) == [(8020, "plexclaw")]


def test_format_blocked_ports_includes_summary_line() -> None:
    lines = port_check.format_blocked_ports([(8020, "plexclaw")])

    assert lines == [
        "[run.sh] Port 8020 already in use (plexclaw).",
        "[run.sh] Stop the existing process or free the port, then retry.",
    ]


def test_format_blocked_ports_returns_empty_for_no_blocked_ports() -> None:
    assert port_check.format_blocked_ports([]) == []


def test_blocked_ports_sets_reuseaddr_before_bind() -> None:
    sock = MagicMock()
    with patch("socket.socket", return_value=sock):
        port_check.blocked_ports(((8020, "plexclaw"),))

    sock.setsockopt.assert_called_once_with(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )
    sock.bind.assert_called_once_with(("127.0.0.1", 8020))
    sock.close.assert_called_once()
