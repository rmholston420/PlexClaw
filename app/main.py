"""PlexClaw FastAPI backend – port 8020."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.request
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app import fs_routes
from app import runtime_sdk as runtime
from app.archive_normalizer import normalize_session, normalize_session_list
from app.config import (
    get_allowed_hosts,
    get_allowed_origins,
    get_ollama_base_url,
    get_vllm_base_url,
)
from app.event_store import init_db, query_events, search_events
from app.provider_defaults import DEFAULT_CLOUD_MODELS
from app.schemas import (
    PROTOCOL_VERSION,
    RenameRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionUpdateRequest,
    TagRequest,
    WSEnvelope,
)
from app.websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    stop_reaper = asyncio.Event()

    async def _session_reaper_loop() -> None:
        try:
            while not stop_reaper.is_set():
                try:
                    await runtime.reap_idle_sessions()
                except Exception as exc:
                    logging.warning("session reaper loop error: %s", exc)
                try:
                    await asyncio.wait_for(
                        stop_reaper.wait(),
                        timeout=runtime.get_reap_interval_seconds(),
                    )
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise

    reaper_task = asyncio.create_task(_session_reaper_loop())
    try:
        yield
    finally:
        stop_reaper.set()
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="PlexClaw Bridge",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(fs_routes.router)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_allowed_hosts(),
)





# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "protocol_version": PROTOCOL_VERSION}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@app.get("/api/diag/runtime")
@app.get("/api/runtime/diag")
async def runtime_diagnostics() -> dict:
    sessions = runtime.list_live_sessions()
    now = time.monotonic()
    items = []
    for s in sessions:
        items.append(
            {
                "session_id": s.id,
                "model": s.model,
                "provider": s.provider,
                "status": s.status,
                "mock_mode": s.mock_mode,
                "permission_mode": s.permission_mode,
                "cwd": s.cwd,
                "tag": s.tag,
                "title": s.title,
                "connections": ws_manager.connection_count(s.id),
                "idle_seconds": round(max(0.0, now - s.last_activity_at), 3),
            }
        )

    return {
        "ok": True,
        "protocol_version": PROTOCOL_VERSION,
        "live_session_count": len(sessions),
        "websocket_session_count": ws_manager.session_count(),
        "sessions": items,
    }


@app.get("/api/sessions")
async def list_sessions() -> list:
    """Return all currently live (in-memory) sessions.

    Useful for the frontend to recover tab state after a page refresh
    and to display session badges in the top bar.
    """
    now = time.monotonic()
    return [
        {
            "session_id": s.id,
            "model": s.model,
            "provider": s.provider,
            "status": s.status,
            "mock_mode": s.mock_mode,
            "permission_mode": s.permission_mode,
            "cwd": s.cwd,
            "tag": s.tag,
            "title": s.title,
            "connections": ws_manager.connection_count(s.id),
            "idle_seconds": round(max(0.0, now - s.last_activity_at), 3),
        }
        for s in runtime.list_live_sessions()
    ]


@app.post("/api/sessions", response_model=SessionCreateResponse)
async def create_session(req: SessionCreateRequest) -> SessionCreateResponse:
    try:
        session = await runtime.create_session(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    provider_env = runtime._provider_env(session.provider)
    provider_base_url = provider_env.get("ANTHROPIC_BASE_URL")
    tool_search_mode = req.tool_search_mode
    tool_search_active = (
        bool(tool_search_mode) if tool_search_mode is not None else None
    )

    return SessionCreateResponse(
        session_id=session.id,
        status="created",
        protocol_version=PROTOCOL_VERSION,
        mock_mode=session.mock_mode,
        model=session.model,
        provider=session.provider,
        provider_base_url=provider_base_url,
        tool_search_mode=tool_search_mode,
        tool_search_active=tool_search_active,
        permission_mode=session.permission_mode,
        cwd=session.cwd,
    )


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, req: SessionUpdateRequest) -> dict:
    try:
        session = await runtime.update_session(
            session_id,
            permission_mode=req.permission_mode,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "session_id": session.id,
        "status": session.status,
        "permission_mode": session.permission_mode,
    }


@app.post("/api/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str) -> dict:
    try:
        await runtime.interrupt_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    try:
        await runtime.delete_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/sessions/{session_id}/context")
async def upload_context_file(session_id: str, file: UploadFile = File(...)) -> dict:
    try:
        max_upload = 200 * 1024 + 1
        raw = await file.read(max_upload)
        if len(raw) > 200 * 1024:
            raise HTTPException(status_code=413, detail="file exceeds 200KB limit")
        text = raw.decode("utf-8")
        item = runtime.add_context_file(
            session_id, file.filename or "attachment.txt", text
        )
        return {
            "ok": True,
            "file": item,
            "files": runtime.list_context_files(session_id),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Only UTF-8 text files are supported"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/context")
async def list_context(session_id: str) -> dict:
    try:
        return {"files": runtime.list_context_files(session_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/sessions/{session_id}/context/{filename}")
async def delete_context_file(session_id: str, filename: str) -> dict:
    try:
        runtime.remove_context_file(session_id, filename)
        return {"ok": True, "files": runtime.list_context_files(session_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Providers / models
# ---------------------------------------------------------------------------


def get_cloud_models() -> list[str]:
    raw = os.getenv("PLEXCLAW_CLOUD_MODELS", "").strip()
    if not raw:
        return DEFAULT_CLOUD_MODELS

    models = [item.strip() for item in raw.split(",") if item.strip()]
    return models or DEFAULT_CLOUD_MODELS


async def _fetch_ollama_models() -> list[str]:
    base = get_ollama_base_url()
    try:

        def _load():
            with urllib.request.urlopen(f"{base}/api/tags", timeout=2.0) as res:
                return json.loads(res.read().decode("utf-8"))

        data = await asyncio.to_thread(_load)
        return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


async def _fetch_vllm_models() -> list[str]:
    base = get_vllm_base_url()
    try:

        def _load():
            with urllib.request.urlopen(f"{base}/v1/models", timeout=2.0) as res:
                return json.loads(res.read().decode("utf-8"))

        data = await asyncio.to_thread(_load)
        return [m.get("id") for m in data.get("data", []) if m.get("id")]
    except Exception:
        return []


@app.get("/api/providers")
async def get_providers() -> dict:
    ollama_base = get_ollama_base_url()
    vllm_base = get_vllm_base_url()
    ollama_models, vllm_models = await asyncio.gather(
        _fetch_ollama_models(),
        _fetch_vllm_models(),
    )
    return {
        "default_provider": "cloud",
        "providers": {
            "cloud": {"label": "Cloud", "models": get_cloud_models()},
            "ollama": {
                "label": "Ollama",
                "base_url": ollama_base,
                "models": ollama_models,
            },
            "vllm": {"label": "vLLM", "base_url": vllm_base, "models": vllm_models},
        },
    }


@app.get("/api/providers/health")
async def get_provider_health() -> dict:
    ollama_models, vllm_models = await asyncio.gather(
        _fetch_ollama_models(),
        _fetch_vllm_models(),
    )
    return {
        "cloud": {"ok": True},
        "ollama": {"ok": bool(ollama_models), "models": len(ollama_models)},
        "vllm": {"ok": bool(vllm_models), "models": len(vllm_models)},
    }


def _render_session_markdown(session_id: str, events: list[dict]) -> str:
    lines = [f"# Session {session_id}", ""]

    tool_inputs: dict[str, dict] = {}
    for evt in events:
        payload = evt.get("payload", {})
        if (
            evt.get("type") == "tool.delta"
            and payload.get("tool_id") is not None
            and "tool_input" in payload
        ):
            tool_inputs[str(payload["tool_id"])] = payload.get("tool_input") or {}

    assistant_buf: list[str] = []

    def flush_assistant() -> None:
        nonlocal assistant_buf
        text = "".join(assistant_buf).strip()
        if text:
            lines.append("## Assistant")
            lines.append("")
            lines.append(text)
            lines.append("")
        assistant_buf = []

    for evt in events:
        etype = evt.get("type")
        payload = evt.get("payload", {})

        if etype == "system.message":
            flush_assistant()
            lines.append("## System")
            lines.append("")
            lines.append(str(payload.get("text", "")))
            lines.append("")
        elif etype == "assistant.delta":
            assistant_buf.append(str(payload.get("text", "")))
        elif etype == "tool.started":
            flush_assistant()
            tool_id = str(payload.get("tool_id", ""))
            final_input = tool_inputs.get(tool_id, payload.get("tool_input", {}))
            lines.append(f"## Tool: {payload.get('tool_name', 'tool')}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(final_input, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")
        elif etype == "tool.completed":
            flush_assistant()
            lines.append(f"## Tool Output: {payload.get('tool_name', 'tool')}")
            lines.append("")
            lines.append("```")
            lines.append(str(payload.get("output", "")))
            lines.append("```")
            lines.append("")

        elif etype == "tool.permission_required":
            flush_assistant()
            tool_name = payload.get("tool_name", "tool")
            tool_input = payload.get("tool_input", {})
            lines.append(f"## Tool Approval Required: {tool_name}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(tool_input, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

        elif etype == "tool.permission_decided":
            flush_assistant()
            tool_name = payload.get("tool_name", "tool")
            decision = str(payload.get("decision", "unknown"))
            lines.append(f"## Tool Approval Decision: {tool_name}")
            lines.append("")
            lines.append(decision)
            lines.append("")

        elif etype == "session.failed":
            flush_assistant()
            lines.append("## Error")
            lines.append("")
            lines.append(str(payload.get("error", "")))
            lines.append("")

    flush_assistant()
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# Event store / replay
# ---------------------------------------------------------------------------


@app.get("/api/search")
async def search_api(q: str = Query(..., min_length=1)) -> list:
    return search_events(q)


@app.get("/api/sessions/{session_id}/export")
async def export_session(session_id: str, format: Literal["json", "md"] = "json"):
    events = query_events(session_id)
    if format == "json":
        return JSONResponse(content={"session_id": session_id, "events": events})
    if format == "md":
        return PlainTextResponse(
            _render_session_markdown(session_id, events),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="format must be 'json' or 'md'")


@app.get("/api/sessions/{session_id}/events")
async def get_events(
    session_id: str,
    event_type: str | None = None,
    since_seq: int | None = None,
) -> list:
    return query_events(session_id, event_type=event_type, since_seq=since_seq)


@app.get("/api/sessions/{session_id}/replay")
async def get_replay(session_id: str) -> list:
    return query_events(session_id)


# ---------------------------------------------------------------------------
# Archive endpoints
# ---------------------------------------------------------------------------


@app.get("/api/archive/sessions")
async def list_archive() -> list:
    raw = await runtime.list_archive_sessions()
    return normalize_session_list(raw)


@app.get("/api/archive/sessions/{session_id}")
async def get_archive_session(session_id: str) -> dict:
    raw = await runtime.get_archive_session(session_id)
    return normalize_session(raw)


@app.get("/api/archive/sessions/{session_id}/messages")
async def get_archive_messages(session_id: str) -> list:
    return await runtime.get_archive_messages(session_id)


@app.get("/api/archive/sessions/{session_id}/replay")
async def get_archive_replay(session_id: str) -> list:
    return await runtime.get_archive_replay_events(session_id)


@app.post("/api/archive/sessions/{session_id}/rename")
async def rename_session(session_id: str, body: RenameRequest) -> dict:
    await runtime.rename_archive_session(session_id, body.title)
    return {"ok": True}


@app.post("/api/archive/sessions/{session_id}/tag")
async def tag_session(session_id: str, body: TagRequest) -> dict:
    await runtime.tag_archive_session(session_id, body.tag)
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    client_protocol = websocket.query_params.get("protocol_version")
    if client_protocol != PROTOCOL_VERSION:
        await websocket.close(
            code=4400,
            reason=f"protocol_version mismatch: server={PROTOCOL_VERSION}",
        )
        return

    session = runtime.get_session(session_id)
    if not session:
        await websocket.close(code=4404, reason="session not found")
        return

    await websocket.accept()
    ws_manager.add(session_id, websocket)
    runtime.touch_session(session)

    # Emit session.ready
    ready = WSEnvelope(
        type="session.ready",
        session_id=session_id,
        seq=session.next_seq(),
        payload={
            "model": session.model,
            "mock_mode": session.mock_mode,
        },
    )
    await runtime._emit(session, ready)

    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid JSON"})
                continue

            msg_type = data.get("type")
            if msg_type == "approve":
                tool_id = data.get("tool_id")
                if tool_id:
                    try:
                        await runtime.approve_tool_call(session_id, tool_id)
                    except KeyError:
                        await websocket.send_json(
                            {"type": "error", "detail": f"no pending tool {tool_id}"}
                        )
                continue
            if msg_type == "reject":
                tool_id = data.get("tool_id")
                if tool_id:
                    try:
                        await runtime.reject_tool_call(session_id, tool_id)
                    except KeyError:
                        await websocket.send_json(
                            {"type": "error", "detail": f"no pending tool {tool_id}"}
                        )
                continue

            prompt = data.get("prompt", "")
            if prompt:
                asyncio.create_task(runtime.submit_prompt(session_id, prompt))
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.remove(session_id, websocket)
