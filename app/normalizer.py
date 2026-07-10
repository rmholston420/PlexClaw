"""Normalize raw Claude SDK event dicts into WSEnvelope protocol payloads.

Mapping:
  text block              -> assistant.delta
  tool_use start          -> tool.started
  tool stream updates     -> tool.delta
  tool result/completion  -> tool.completed
  terminal result         -> assistant.completed
  runtime exceptions      -> session.failed
"""
from __future__ import annotations

from typing import Any

from app.schemas import PROTOCOL_VERSION, WSEnvelope


def _envelope(
    event_type: str,
    session_id: str,
    seq: int,
    payload: dict[str, Any],
) -> WSEnvelope:
    return WSEnvelope(
        type=event_type,
        session_id=session_id,
        seq=seq,
        payload=payload,
        protocol_version=PROTOCOL_VERSION,
    )


def normalize_text_delta(
    session_id: str,
    seq: int,
    text: str,
) -> WSEnvelope:
    return _envelope("assistant.delta", session_id, seq, {"text": text})


def normalize_tool_started(
    session_id: str,
    seq: int,
    tool_id: str,
    tool_name: str,
    tool_input: Any,
) -> WSEnvelope:
    return _envelope(
        "tool.started",
        session_id,
        seq,
        {"tool_id": tool_id, "tool_name": tool_name},
    )


def normalize_tool_delta(
    session_id: str,
    seq: int,
    tool_id: str,
    partial: str,
) -> WSEnvelope:
    return _envelope(
        "tool.delta",
        session_id,
        seq,
        {"tool_id": tool_id, "partial": partial},
    )


def normalize_tool_completed(
    session_id: str,
    seq: int,
    tool_id: str,
    tool_name: str,
    output: Any,
    is_error: bool = False,
) -> WSEnvelope:
    return _envelope(
        "tool.completed",
        session_id,
        seq,
        {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "output": output,
            "is_error": is_error,
        },
    )


def normalize_tool_permission_decided(
    session_id: str,
    seq: int,
    tool_id: str,
    tool_name: str,
    tool_input: Any,
    decision: str,
) -> WSEnvelope:
    return _envelope(
        "tool.permission_decided",
        session_id,
        seq,
        {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "decision": decision,
        },
    )


def normalize_assistant_completed(
    session_id: str,
    seq: int,
    stop_reason: str = "end_turn",
    usage: dict[str, Any] | None = None,
) -> WSEnvelope:
    return _envelope(
        "assistant.completed",
        session_id,
        seq,
        {"stop_reason": stop_reason, "usage": usage or {}},
    )


def normalize_session_failed(
    session_id: str,
    seq: int,
    error: str,
) -> WSEnvelope:
    return _envelope("session.failed", session_id, seq, {"error": error})


def normalize_system_message(
    session_id: str,
    seq: int,
    text: str,
    level: str = "info",
) -> WSEnvelope:
    return _envelope("system.message", session_id, seq, {"text": text, "level": level})
