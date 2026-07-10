"""Environment-backed application configuration helpers."""

from __future__ import annotations

import os

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5555",
    "http://127.0.0.1:5555",
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

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_VLLM_BASE_URL = "http://127.0.0.1:30000"


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def get_vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).rstrip("/")


def get_provider_env(provider: str) -> dict[str, str]:
    env: dict[str, str] = {}
    if provider == "ollama":
        env["ANTHROPIC_BASE_URL"] = get_ollama_base_url()
    elif provider == "vllm":
        env["ANTHROPIC_BASE_URL"] = get_vllm_base_url()
    return env


def get_tool_search_env(mode: str | None) -> dict[str, str]:
    if not mode:
        return {}
    return {"ENABLE_TOOL_SEARCH": mode}

