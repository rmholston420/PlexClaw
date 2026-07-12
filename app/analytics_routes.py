"""Usage analytics — ported from Claudia (AGPL-3.0).

Aggregates token/cost data from the existing event store.
No new tables required — reads from events.payload fields populated by
assistant.completed events emitted by the Claude SDK.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query

from app.config import CLAUDE_PRICING
from app.event_store import _db_lock, _ensure_initialized, _get_conn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ---------------------------------------------------------------------------
# Pricing imported from app.config
# ---------------------------------------------------------------------------

_FALLBACK_PRICING = {
    "input": 3.00,
    "output": 15.00,
    "cache_read": 0.30,
    "cache_write": 3.75,
}


def _get_pricing(model: str) -> dict[str, float]:
    ml = model.lower()
    for prefix, p in CLAUDE_PRICING.items():
        if ml.startswith(prefix):
            return p
    return _FALLBACK_PRICING


def _cost_usd(usage: dict[str, Any], model: str) -> float:
    p = _get_pricing(model)
    inp   = usage.get("input_tokens",      0) or 0
    out   = usage.get("output_tokens",     0) or 0
    cr    = usage.get("cache_read_tokens", 0) or 0
    cw    = usage.get("cache_write_tokens",0) or 0
    return (
        inp  * p["input"]       / 1_000_000
        + out  * p["output"]      / 1_000_000
        + cr   * p["cache_read"]  / 1_000_000
        + cw   * p["cache_write"] / 1_000_000
    )


# ---------------------------------------------------------------------------
# Blocking aggregation (runs in thread)
# ---------------------------------------------------------------------------

def _aggregate_usage() -> dict[str, Any]:
    _ensure_initialized()
    with _db_lock:
        c = _get_conn()
        rows = c.execute(
            """
            SELECT session_id, payload, created_at
            FROM   events
            WHERE  type = 'assistant.completed'
            ORDER  BY created_at ASC
            """
        ).fetchall()

    def _bucket() -> dict[str, Any]:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "cost_usd": 0.0,
            "calls": 0,
        }

    by_model: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_day: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_session: dict[str, dict[str, Any]] = defaultdict(_bucket)
    totals: dict[str, Any] = _bucket()

    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except (json.JSONDecodeError, TypeError):
            continue

        usage = payload.get("usage") or payload.get("token_usage") or {}
        if not usage:
            continue

        model = (payload.get("model") or "unknown").strip()
        created_at = row["created_at"] or ""
        day = created_at[:10]
        session_id = row["session_id"]
        cost = _cost_usd(usage, model)

        for bucket in (by_model[model], by_day[day], by_session[session_id], totals):
            bucket["input_tokens"] += usage.get("input_tokens", 0) or 0
            bucket["output_tokens"] += usage.get("output_tokens", 0) or 0
            bucket["cache_read_tokens"] += usage.get("cache_read_tokens", 0) or 0
            bucket["cache_write_tokens"] += usage.get("cache_write_tokens", 0) or 0
            bucket["cost_usd"] += cost
            bucket["calls"] += 1

    daily_series = [
        {
            "date": day,
            **bucket,
        }
        for day, bucket in sorted(by_day.items(), key=lambda kv: kv[0])
    ]

    return {
        "totals": totals,
        "by_model": dict(sorted(by_model.items(), key=lambda kv: kv[0])),
        "by_day": dict(sorted(by_day.items(), key=lambda kv: kv[0])),
        "by_session": dict(sorted(by_session.items(), key=lambda kv: kv[0])),
        "daily_series": daily_series,
    }



# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_analytics() -> dict:
    """Return aggregated token and cost analytics from the event store."""
    return await asyncio.to_thread(_aggregate_usage)


@router.get("/session/{session_id}")
async def get_session_analytics(session_id: str) -> dict:
    """Return token/cost analytics for a single session."""
    data = await asyncio.to_thread(_aggregate_usage)
    session_data = data["by_session"].get(session_id, {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_write_tokens": 0,
        "cost_usd": 0.0, "calls": 0,
    })
    return {"session_id": session_id, **session_data}


@router.get("/models")
async def get_model_breakdown() -> dict:
    """Return per-model token and cost breakdown."""
    data = await asyncio.to_thread(_aggregate_usage)
    return {"by_model": data["by_model"]}


@router.get("/daily")
async def get_daily_series(
    days: int = Query(default=30, ge=1, le=365)
) -> list:
    """Return daily cost+token series, optionally limited to recent N days."""
    data = await asyncio.to_thread(_aggregate_usage)
    series = data["daily_series"]
    return series[-days:] if len(series) > days else series
