"""PlexClaw FastAPI backend – port 8020."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from contextlib import asynccontextmanager

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
from fastapi.responses import JSONResponse, PlainTextResponse

from app import fs_routes
from app import runtime_sdk as runtime
from app.archive_normalizer import normalize_session, normalize_session_list
from app.event_store import init_db, query_events, search_events
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
    yield


app = FastAPI(
    title="PlexClaw Bridge",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(fs_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
        mock_mode=session.mock_mode,
        model=session.model,
        provider=session.provider,
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
        raw = await file.read()
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
async def export_session(session_id: str, format: str = "json"):
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
