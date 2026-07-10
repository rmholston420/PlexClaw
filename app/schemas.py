"""Protocol schemas for PlexClaw WebSocket bridge."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.provider_defaults import DEFAULT_CLOUD_MODELS

PROTOCOL_VERSION = "0.2.0"

ProviderName = Literal["cloud", "ollama", "vllm"]
PermissionMode = Literal["auto", "manual"]


class WSEnvelope(BaseModel):
    """Stable WebSocket protocol envelope sent to the browser."""

    type: str
    session_id: str
    seq: int
    payload: dict[str, Any]
    protocol_version: str = PROTOCOL_VERSION


class SessionCreateRequest(BaseModel):
    model: str = Field(default=DEFAULT_CLOUD_MODELS[0], min_length=1, max_length=200)
    cwd: str | None = None
    provider: ProviderName = "cloud"
    permission_mode: PermissionMode = "manual"
    tool_search_mode: str | None = None
    system_prompt: str | None = None
    resume_session_id: str | None = None
    fork_session: bool = False

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("model must not be empty")
        return value


class SessionUpdateRequest(BaseModel):
    permission_mode: PermissionMode | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str = "created"
    protocol_version: str = PROTOCOL_VERSION
    mock_mode: bool = False
    model: str
    provider: str
    provider_base_url: str | None = None
    tool_search_mode: str | None = None
    tool_search_active: bool | None = None
    permission_mode: str | None = None
    cwd: str | None = None


class PromptRequest(BaseModel):
    prompt: str
    session_id: str | None = None


class InterruptRequest(BaseModel):
    session_id: str


class RenameRequest(BaseModel):
    title: str


class TagRequest(BaseModel):
    tag: str | None = None
