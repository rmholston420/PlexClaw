import pytest

from app.config import (
    DEFAULT_ALLOWED_HOSTS,
    DEFAULT_ALLOWED_ORIGINS,
    get_allowed_hosts,
    get_allowed_origins,
    get_ollama_base_url,
    get_provider_env,
    get_tool_search_env,
    get_vllm_base_url,
)


def test_get_allowed_origins_defaults(monkeypatch):
    monkeypatch.delenv("PLEXCLAW_ALLOWED_ORIGINS", raising=False)
    assert get_allowed_origins() == DEFAULT_ALLOWED_ORIGINS


def test_get_allowed_origins_parses_csv(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_ALLOWED_ORIGINS",
        " http://frontend.local , http://localhost:5555 ",
    )
    assert get_allowed_origins() == [
        "http://frontend.local",
        "http://localhost:5555",
    ]


def test_get_allowed_hosts_defaults(monkeypatch):
    monkeypatch.delenv("PLEXCLAW_ALLOWED_HOSTS", raising=False)
    assert get_allowed_hosts() == DEFAULT_ALLOWED_HOSTS


def test_get_allowed_hosts_parses_csv(monkeypatch):
    monkeypatch.setenv(
        "PLEXCLAW_ALLOWED_HOSTS",
        " testserver , localhost , 127.0.0.1 ",
    )
    assert get_allowed_hosts() == [
        "testserver",
        "localhost",
        "127.0.0.1",
    ]



def test_get_ollama_base_url_defaults(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert get_ollama_base_url() == "http://127.0.0.1:11434"


def test_get_vllm_base_url_defaults(monkeypatch):
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    assert get_vllm_base_url() == "http://127.0.0.1:30000"


def test_get_provider_env_for_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434/")
    assert get_provider_env("ollama") == {
        "ANTHROPIC_BASE_URL": "http://ollama.local:11434"
    }


def test_get_provider_env_for_vllm(monkeypatch):
    monkeypatch.setenv("VLLM_BASE_URL", "http://vllm.local:30000/")
    assert get_provider_env("vllm") == {
        "ANTHROPIC_BASE_URL": "http://vllm.local:30000"
    }


def test_get_provider_env_for_cloud():
    assert get_provider_env("cloud") == {}



@pytest.mark.parametrize("provider", ["ollama", "vllm"])
def test_get_provider_env_base_url_override_short_circuits(provider, monkeypatch):
    monkeypatch.setattr(
        "app.config.get_ollama_base_url",
        lambda: "http://should-not-be-used:11434",
    )
    monkeypatch.setattr(
        "app.config.get_vllm_base_url",
        lambda: "http://should-not-be-used:8000",
    )

    assert get_provider_env(provider, "  http://override.local:9999/  ") == {
        "ANTHROPIC_BASE_URL": "http://override.local:9999"
    }


def test_get_tool_search_env_empty():
    assert get_tool_search_env(None) == {}
    assert get_tool_search_env("") == {}


def test_get_tool_search_env_passthrough():
    assert get_tool_search_env("false") == {"ENABLE_TOOL_SEARCH": "false"}

