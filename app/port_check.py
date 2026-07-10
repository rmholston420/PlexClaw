from __future__ import annotations

import socket
from collections.abc import Iterable

DEFAULT_PORTS: tuple[tuple[int, str], ...] = (
    (8020, "backend"),
    (5555, "frontend"),
)


def blocked_ports(
    ports: Iterable[tuple[int, str]] = DEFAULT_PORTS,
) -> list[tuple[int, str]]:
    blocked: list[tuple[int, str]] = []

    for port, label in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            blocked.append((port, label))
        finally:
            sock.close()

    return blocked


def format_blocked_ports(
    blocked: Iterable[tuple[int, str]],
) -> list[str]:
    items = list(blocked)
    lines = [
        f"[run.sh] Port {port} already in use ({label})."
        for port, label in items
    ]
    if items:
        lines.append(
            "[run.sh] Stop the existing process or free the port, then retry."
        )
    return lines
