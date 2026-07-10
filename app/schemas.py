"""Protocol schemas for PlexClaw WebSocket bridge."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid

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
    cwd: Optional[str] = None
    provider: str = "cloud"
    permission_mode: str = "manual"
    system_prompt: Optional[str] = None
    resume_session_id: Optional[str] = None
    fork_session: bool = False



class SessionUpdateRequest(BaseModel):
    permission_mode: Optional[str] = None
class SessionCreateResponse(BaseModel):
    session_id: str
    status: str = "created"
    protocol_version: str = PROTOCOL_VERSION


class PromptRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


class InterruptRequest(BaseModel):
    session_id: str


class RenameRequest(BaseModel):
    title: str


class TagRequest(BaseModel):
    tag: Optional[str] = None
