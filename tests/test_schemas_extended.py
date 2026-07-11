"""Unit tests for app/schemas.py.

Covers:
  - WSEnvelope round-trip serialization
  - SessionCreateRequest defaults and field_validator (normalize_model)
  - SessionCreateRequest rejects empty / whitespace-only model
  - SessionUpdateRequest optional fields
  - SessionCreateResponse round-trip
  - PromptRequest, InterruptRequest, RenameRequest, TagRequest
  - PROTOCOL_VERSION format sanity
  - ProviderName / PermissionMode literals
  - provider_defaults: DEFAULT_CLOUD_MODELS non-empty, first element is str
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import DEFAULT_OLLAMA_MODEL
from app.provider_defaults import DEFAULT_CLOUD_MODELS
from app.schemas import (
    PROTOCOL_VERSION,
    InterruptRequest,
    PromptRequest,
    RenameRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionUpdateRequest,
    TagRequest,
    WSEnvelope,
)


def test_protocol_version_is_semver_like():
    parts = PROTOCOL_VERSION.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit(), f"non-numeric semver part: {part!r}"


# ---------------------------------------------------------------------------
# WSEnvelope
# ---------------------------------------------------------------------------


def test_ws_envelope_round_trip():
    env = WSEnvelope(
        type="assistant.delta",
        session_id="abc123",
        seq=5,
        payload={"text": "hello"},
    )
    data = env.model_dump()
    assert data["protocol_version"] == PROTOCOL_VERSION
    assert data["seq"] == 5
    assert data["payload"]["text"] == "hello"


def test_ws_envelope_model_dump_json_is_valid_json():
    import json
    env = WSEnvelope(type="t", session_id="s", seq=1, payload={})
    raw = env.model_dump_json()
    parsed = json.loads(raw)
    assert parsed["session_id"] == "s"


# ---------------------------------------------------------------------------
# SessionCreateRequest – validator
# ---------------------------------------------------------------------------


def test_session_create_request_defaults():
    req = SessionCreateRequest()
    assert req.model == DEFAULT_OLLAMA_MODEL
    assert req.provider == "ollama"
    assert req.permission_mode == "manual"
    assert req.cwd is None
    assert req.fork_session is False


def test_session_create_request_strips_whitespace_from_model():
    req = SessionCreateRequest(model="  claude-opus-4-5  ")
    assert req.model == "claude-opus-4-5"


def test_session_create_request_rejects_empty_model():
    with pytest.raises(ValidationError):
        SessionCreateRequest(model="")


def test_session_create_request_rejects_whitespace_only_model():
    with pytest.raises(ValidationError):
        SessionCreateRequest(model="   ")


def test_session_create_request_rejects_model_over_200_chars():
    with pytest.raises(ValidationError):
        SessionCreateRequest(model="x" * 201)


def test_session_create_request_custom_fields():
    req = SessionCreateRequest(
        model="claude-haiku-4-5",
        provider="ollama",
        permission_mode="auto",
        cwd="/tmp",
        fork_session=True,
        system_prompt="Be brief.",
        resume_session_id="prev-123",
        tool_search_mode="semantic",
    )
    assert req.provider == "ollama"
    assert req.permission_mode == "auto"
    assert req.cwd == "/tmp"
    assert req.fork_session is True
    assert req.system_prompt == "Be brief."
    assert req.resume_session_id == "prev-123"
    assert req.tool_search_mode == "semantic"


def test_session_create_request_rejects_invalid_provider():
    with pytest.raises(ValidationError):
        SessionCreateRequest(provider="openai")  # not in Literal


def test_session_create_request_rejects_invalid_permission_mode():
    with pytest.raises(ValidationError):
        SessionCreateRequest(permission_mode="yolo")


# ---------------------------------------------------------------------------
# SessionUpdateRequest
# ---------------------------------------------------------------------------


def test_session_update_request_all_none_by_default():
    req = SessionUpdateRequest()
    assert req.permission_mode is None


def test_session_update_request_accepts_valid_mode():
    req = SessionUpdateRequest(permission_mode="auto")
    assert req.permission_mode == "auto"


# ---------------------------------------------------------------------------
# SessionCreateResponse
# ---------------------------------------------------------------------------


def test_session_create_response_defaults():
    resp = SessionCreateResponse(
        session_id="xyz",
        model="claude-sonnet-4-5",
        provider="cloud",
    )
    assert resp.status == "created"
    assert resp.protocol_version == PROTOCOL_VERSION
    assert resp.mock_mode is False
    assert resp.provider_base_url is None


# ---------------------------------------------------------------------------
# Other request models
# ---------------------------------------------------------------------------


def test_prompt_request():
    req = PromptRequest(prompt="hello", session_id="s1")
    assert req.prompt == "hello"
    assert req.session_id == "s1"


def test_prompt_request_session_id_optional():
    req = PromptRequest(prompt="hi")
    assert req.session_id is None


def test_interrupt_request():
    req = InterruptRequest(session_id="s2")
    assert req.session_id == "s2"


def test_rename_request():
    req = RenameRequest(title="My Session")
    assert req.title == "My Session"


def test_tag_request_with_tag():
    req = TagRequest(tag="important")
    assert req.tag == "important"


def test_tag_request_tag_none():
    req = TagRequest(tag=None)
    assert req.tag is None


# ---------------------------------------------------------------------------
# provider_defaults
# ---------------------------------------------------------------------------


def test_default_cloud_models_non_empty():
    assert len(DEFAULT_CLOUD_MODELS) >= 1


def test_default_cloud_models_are_strings():
    for m in DEFAULT_CLOUD_MODELS:
        assert isinstance(m, str) and len(m) > 0


def test_default_cloud_models_remain_available_for_explicit_cloud_sessions():
    req = SessionCreateRequest(model=DEFAULT_CLOUD_MODELS[0], provider="cloud")
    assert req.model == DEFAULT_CLOUD_MODELS[0]
    assert req.provider == "cloud"
