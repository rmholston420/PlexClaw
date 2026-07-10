"""PlexClaw FastAPI backend – port 8020."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from typing import Optional


from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import runtime_sdk as runtime
from app.archive_normalizer import normalize_session, normalize_session_list
from app.event_store import init_db, query_events
from app.schemas import (
    PROTOCOL_VERSION,
    InterruptRequest,
    RenameRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    TagRequest,
    WSEnvelope,
)
from app.websocket_manager import ws_manager
from app import fs_routes

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="PlexClaw Bridge", version="0.2.0")

app.include_router(fs_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "protocol_version": PROTOCOL_VERSION}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@app.post("/api/sessions", response_model=SessionCreateResponse)
async def create_session(req: SessionCreateRequest) -> SessionCreateResponse:
    try:
        session = await runtime.create_session(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SessionCreateResponse(
        session_id=session.id,
        status="created",
        protocol_version=PROTOCOL_VERSION,
    )


@app.post("/api/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str) -> dict:
    try:
        await runtime.interrupt_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/sessions/{session_id}/model/{model}")
async def change_model(session_id: str, model: str) -> dict:
    session = runtime.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.model = model
    return {"ok": True, "model": model}



# ---------------------------------------------------------------------------
# Providers / models
# ---------------------------------------------------------------------------


CLOUD_MODELS = [
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-haiku-4-5",
]


async def _fetch_ollama_models() -> list[str]:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        def _load():
            with urllib.request.urlopen(f"{base}/api/tags", timeout=2.0) as res:
                return json.loads(res.read().decode("utf-8"))
        data = await asyncio.to_thread(_load)
        return [m.get("name") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


async def _fetch_vllm_models() -> list[str]:
    base = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:30000").rstrip("/")
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
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    vllm_base = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:30000").rstrip("/")
    ollama_models, vllm_models = await asyncio.gather(
        _fetch_ollama_models(),
        _fetch_vllm_models(),
    )
    return {
        "default_provider": "cloud",
        "providers": {
            "cloud": {"label": "Cloud", "models": CLOUD_MODELS},
            "ollama": {"label": "Ollama", "base_url": ollama_base, "models": ollama_models},
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


# ---------------------------------------------------------------------------
# Event store / replay
# ---------------------------------------------------------------------------


@app.get("/api/sessions/{session_id}/events")
async def get_events(
    session_id: str,
    event_type: Optional[str] = None,
    since_seq: Optional[int] = None,
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
    await websocket.accept()
    ws_manager.add(session_id, websocket)

    session = runtime.get_session(session_id)
    if not session:
        await websocket.send_text(
            WSEnvelope(
                type="session.failed",
                session_id=session_id,
                seq=0,
                payload={"error": "Session not found"},
            ).model_dump_json()
        )
        await websocket.close()
        return

    # Emit session.ready
    ready = WSEnvelope(
        type="session.ready",
        session_id=session_id,
        seq=session.next_seq(),
        payload={"model": session.model},
    )
    await websocket.send_text(ready.model_dump_json())

    try:
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)

            msg_type = data.get("type")
            if msg_type == "approve":
                tool_id = data.get("tool_id")
                if tool_id:
                    await runtime.approve_tool_call(session_id, tool_id)
                continue
            if msg_type == "reject":
                tool_id = data.get("tool_id")
                if tool_id:
                    await runtime.reject_tool_call(session_id, tool_id)
                continue

            prompt = data.get("prompt", "")
            if prompt:
                asyncio.create_task(runtime.submit_prompt(session_id, prompt))
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.remove(session_id, websocket)
