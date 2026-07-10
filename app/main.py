"""PlexClaw FastAPI backend – port 8020."""
from __future__ import annotations

import asyncio
import json
import logging
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

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="PlexClaw Bridge", version="0.2.0")

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
    session = await runtime.create_session(req)
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
            prompt = data.get("prompt", "")
            if prompt:
                asyncio.create_task(runtime.submit_prompt(session_id, prompt))
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.remove(session_id, websocket)
