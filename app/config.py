"""Environment-backed application configuration helpers."""

from __future__ import annotations

import os

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8020",
    "http://127.0.0.1:8020",
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
DEFAULT_OLLAMA_MODEL = "qwen3:latest"
DEFAULT_VLLM_MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def get_vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL", DEFAULT_VLLM_BASE_URL).rstrip("/")


def get_provider_env(
    provider: str,
    base_url_override: str | None = None,
) -> dict[str, str]:
    env: dict[str, str] = {}
    override = (base_url_override or "").strip().rstrip("/")
    if override and provider in {"ollama", "vllm"}:
        env["ANTHROPIC_BASE_URL"] = override
        return env
    if provider == "ollama":
        env["ANTHROPIC_BASE_URL"] = get_ollama_base_url()
    elif provider == "vllm":
        env["ANTHROPIC_BASE_URL"] = get_vllm_base_url()
    return env


def get_default_local_model(provider: str) -> str:
    if provider == "vllm":
        value = os.getenv("PLEXCLAW_VLLM_MODEL", DEFAULT_VLLM_MODEL).strip()
        return value or DEFAULT_VLLM_MODEL

    value = os.getenv("PLEXCLAW_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
    return value or DEFAULT_OLLAMA_MODEL


def get_tool_search_env(mode: str | None) -> dict[str, str]:
    if not mode:
        return {}
    return {"ENABLE_TOOL_SEARCH": mode}

