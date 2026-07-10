"""Normalize raw SDK archive session metadata into a canonical frontend shape.

Canonical fields:
  id, title, summary, tag, created_at, updated_at,
  cwd, root_session_id, message_count, model, raw
"""
from __future__ import annotations

from typing import Any


def normalize_session(raw: Any) -> dict[str, Any]:
    """Accept a dict or object-style session metadata record."""
    if not isinstance(raw, dict):
        try:
            raw = vars(raw)
        except TypeError:
            raw = {}

    def _get(*keys: str, default: Any = None) -> Any:
        for k in keys:
            v = raw.get(k)
            if v is not None:
                return v
        return default

    return {
        "id": _get("id", "session_id", default=""),
        "title": _get("title", "name", default="Untitled session"),
        "summary": _get("summary", "description", default=""),
        "tag": _get("tag", default=None),
        "created_at": _get("created_at", "createdAt", "created", default=None),
        "updated_at": _get("updated_at", "updatedAt", "updated", default=None),
        "cwd": _get("cwd", "working_directory", default=None),
        "root_session_id": _get("root_session_id", "rootSessionId", default=None),
        "message_count": _get("message_count", "messageCount", "num_messages", default=0),
        "model": _get("model", "model_name", default=None),
        "raw": raw,
    }


def normalize_session_list(
    sessions: list[Any],
) -> list[dict[str, Any]]:
    """Normalize a list and sort descending by updated_at."""
    normalized = [normalize_session(s) for s in sessions]
    return sorted(
        normalized,
        key=lambda s: s["updated_at"] or "",
        reverse=True,
    )
