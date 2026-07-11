"""Tests for provider defaults and SessionCreateRequest local-first behavior."""
from __future__ import annotations

from app.config import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_VLLM_MODEL,
    get_default_local_model,
)
from app.provider_defaults import DEFAULT_CLOUD_MODELS
from app.schemas import SessionCreateRequest


def test_default_cloud_models_is_non_empty_list():
    assert isinstance(DEFAULT_CLOUD_MODELS, list)
    assert len(DEFAULT_CLOUD_MODELS) >= 1


def test_default_cloud_models_all_strings():
    for model in DEFAULT_CLOUD_MODELS:
        assert isinstance(model, str), f"Expected str, got {type(model)}"


def test_default_cloud_models_no_empty_strings():
    for model in DEFAULT_CLOUD_MODELS:
        assert model.strip(), f"Empty model string found: {model!r}"


def test_default_cloud_models_no_duplicates():
    assert len(DEFAULT_CLOUD_MODELS) == len(set(DEFAULT_CLOUD_MODELS)), (
        "Duplicate model IDs found in DEFAULT_CLOUD_MODELS"
    )


def test_default_cloud_models_contain_claude_strings():
    for model in DEFAULT_CLOUD_MODELS:
        assert "claude" in model.lower(), f"Unexpected model ID: {model!r}"


def test_session_create_request_defaults_to_ollama_provider():
    req = SessionCreateRequest()
    assert req.provider == "ollama"


def test_session_create_request_defaults_to_ollama_model():
    req = SessionCreateRequest()
    assert req.model == DEFAULT_OLLAMA_MODEL


def test_get_default_local_model_uses_vllm_default():
    assert get_default_local_model("vllm") == DEFAULT_VLLM_MODEL
