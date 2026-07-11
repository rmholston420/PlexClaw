"""Tests for app/provider_defaults.py.

Verifies the shape and content invariants of DEFAULT_CLOUD_MODELS.
"""
from __future__ import annotations

from app.provider_defaults import DEFAULT_CLOUD_MODELS


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
    assert len(DEFAULT_CLOUD_MODELS) == len(set(DEFAULT_CLOUD_MODELS)), \
        "Duplicate model IDs found in DEFAULT_CLOUD_MODELS"


def test_default_cloud_models_first_is_default():
    """schemas.py uses DEFAULT_CLOUD_MODELS[0] as the SessionCreateRequest default."""
    from app.schemas import SessionCreateRequest
    req = SessionCreateRequest()
    assert req.model == DEFAULT_CLOUD_MODELS[0]


def test_default_cloud_models_contain_claude_strings():
    """Every entry should look like a Claude model identifier."""
    for model in DEFAULT_CLOUD_MODELS:
        assert "claude" in model.lower(), f"Unexpected model ID: {model!r}"
