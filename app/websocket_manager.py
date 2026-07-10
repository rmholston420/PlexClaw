"""Per-session WebSocket fanout manager."""

from __future__ import annotations

from fastapi import WebSocket

from app.schemas import WSEnvelope


class WebSocketManager:
    def __init__(self) -> None:
        self._sessions: dict[str, list[WebSocket]] = {}

    def add(self, session_id: str, ws: WebSocket) -> None:
        self._sessions.setdefault(session_id, []).append(ws)

    def remove(self, session_id: str, ws: WebSocket) -> None:
        conns = self._sessions.get(session_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, envelope: WSEnvelope) -> None:
        data = envelope.model_dump_json()
        conns = list(self._sessions.get(envelope.session_id, []))
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove(envelope.session_id, ws)

    async def send_to(self, session_id: str, envelope: WSEnvelope) -> None:
        await self.broadcast(envelope)


ws_manager = WebSocketManager()
