"""Normalize raw SDK archive session metadata into a canonical frontend shape.

Canonical fields:
  id, title, summary, tag, created_at, updated_at,
  cwd, root_session_id, message_count, model, raw
"""

from __future__ import annotations

from typing import Any


def normalize_session(raw: Any) -> dict[str, Any]:
    """Accept a dict or object-style session metadata record."""

    def _get(*keys: str, default: Any = None) -> Any:
        if isinstance(raw, dict):
            for k in keys:
                v = raw.get(k)
                if v is not None:
                    return v
            return default

        for k in keys:
            try:
                v = getattr(raw, k)
            except Exception:
                v = None
            if v is not None:
                return v
        return default

    session_id = _get("session_id", "id", default="")
    updated_at = _get(
        "updated_at", "updatedAt", "updated", "last_modified", default=None
    )
    created_at = _get("created_at", "createdAt", "created", default=None)
    title = _get("title", "custom_title", "name", default=None) or _get(
        "summary", "first_prompt", default="Untitled session"
    )

    raw_dict = (
        raw
        if isinstance(raw, dict)
        else {
            "session_id": _get("session_id", default=None),
            "summary": _get("summary", default=None),
            "custom_title": _get("custom_title", default=None),
            "last_modified": _get("last_modified", default=None),
            "created_at": _get("created_at", default=None),
            "cwd": _get("cwd", default=None),
            "tag": _get("tag", default=None),
            "first_prompt": _get("first_prompt", default=None),
            "git_branch": _get("git_branch", default=None),
            "file_size": _get("file_size", default=None),
        }
    )

    return {
        "id": session_id,
        "session_id": session_id,
        "title": title,
        "summary": _get("summary", "description", default=""),
        "tag": _get("tag", default=None),
        "created_at": created_at,
        "updated_at": updated_at,
        "last_modified": updated_at,
        "cwd": _get("cwd", "working_directory", default=None),
        "root_session_id": _get("root_session_id", "rootSessionId", default=None),
        "message_count": _get(
            "message_count", "messageCount", "num_messages", default=0
        ),
        "model": _get("model", "model_name", default=None),
        "raw": raw_dict,
    }


def normalize_session_list(
    sessions: list[Any],
) -> list[dict[str, Any]]:
    """Normalize a list and sort deterministically by recency."""
    normalized = [normalize_session(s) for s in sessions]

    def _ts(value: object) -> float:
        if value is None:
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        try:
            from datetime import datetime

            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    return sorted(
        normalized,
        key=lambda s: (
            -_ts(s.get("updated_at")),
            -_ts(s.get("created_at")),
            str(s.get("id") or s.get("session_id") or ""),
        ),
    )
