"""Protocol schemas for PlexClaw WebSocket bridge."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

PROTOCOL_VERSION = "0.2.0"


class WSEnvelope(BaseModel):
    """Stable WebSocket protocol envelope sent to the browser."""

    type: str
    session_id: str
    seq: int
    payload: dict[str, Any]
    protocol_version: str = PROTOCOL_VERSION


class SessionCreateRequest(BaseModel):
    model: str = "claude-sonnet-4-5"
    cwd: str | None = None
    provider: str = "cloud"
    permission_mode: str = "manual"
    system_prompt: str | None = None
    resume_session_id: str | None = None
    fork_session: bool = False


class SessionUpdateRequest(BaseModel):
    permission_mode: str | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str = "created"
    protocol_version: str = PROTOCOL_VERSION


class PromptRequest(BaseModel):
    prompt: str
    session_id: str | None = None


class InterruptRequest(BaseModel):
    session_id: str


class RenameRequest(BaseModel):
    title: str


class TagRequest(BaseModel):
    tag: str | None = None
