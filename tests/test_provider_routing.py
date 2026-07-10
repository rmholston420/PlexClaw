from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas import SessionCreateRequest
from app import runtime_sdk as runtime


class DummyClient:
    def __init__(self, options):
        self.options = options


@pytest.fixture(autouse=True)
def clear_sessions():
    runtime._sessions.clear()
    yield
    runtime._sessions.clear()


@pytest.mark.asyncio
async def test_create_session_cloud_has_no_base_url_env(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(runtime, "ClaudeSDKClient", DummyClient)

    req = SessionCreateRequest(
        model="claude-sonnet-4-5",
        cwd=str(tmp_path),
        provider="cloud",
    )
    session = await runtime.create_session(req)

    assert session.provider == "cloud"
    assert isinstance(session._client, DummyClient)
    assert session._client.options.env == {}


@pytest.mark.asyncio
async def test_create_session_ollama_sets_anthropic_base_url(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(runtime, "ClaudeSDKClient", DummyClient)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/")

    req = SessionCreateRequest(
        model="llama3.1",
        cwd=str(tmp_path),
        provider="ollama",
    )
    session = await runtime.create_session(req)

    assert session.provider == "ollama"
    assert session._client.options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_create_session_vllm_sets_anthropic_base_url(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(runtime, "ClaudeSDKClient", DummyClient)
    monkeypatch.setenv("VLLM_BASE_URL", "http://127.0.0.1:30000/")

    req = SessionCreateRequest(
        model="qwen2.5-coder",
        cwd=str(tmp_path),
        provider="vllm",
    )
    session = await runtime.create_session(req)

    assert session.provider == "vllm"
    assert session._client.options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:30000"


@pytest.mark.asyncio
async def test_create_session_ollama_uses_default_base_url_when_env_unset(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(runtime, "ClaudeSDKClient", DummyClient)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    req = SessionCreateRequest(
        model="llama3.1",
        cwd=str(tmp_path),
        provider="ollama",
    )
    session = await runtime.create_session(req)

    assert session._client.options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_create_session_vllm_uses_default_base_url_when_env_unset(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(runtime, "_SDK_AVAILABLE", True)
    monkeypatch.setattr(runtime, "ClaudeSDKClient", DummyClient)
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)

    req = SessionCreateRequest(
        model="qwen2.5-coder",
        cwd=str(tmp_path),
        provider="vllm",
    )
    session = await runtime.create_session(req)

    assert session._client.options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:30000"
