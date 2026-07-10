"""Environment-backed application configuration helpers."""

from __future__ import annotations

import os

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5555",
]

DEFAULT_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "testserver",
]


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_allowed_origins() -> list[str]:
    return _parse_csv_env("PLEXCLAW_ALLOWED_ORIGINS") or DEFAULT_ALLOWED_ORIGINS


def get_allowed_hosts() -> list[str]:
    return _parse_csv_env("PLEXCLAW_ALLOWED_HOSTS") or DEFAULT_ALLOWED_HOSTS
