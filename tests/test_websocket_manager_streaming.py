from __future__ import annotations

from pathlib import Path


def test_websocket_manager_module_contract() -> None:
    text = Path("app/websocket_manager.py").read_text()
    assert 'Per-session WebSocket fanout manager.' in text
    assert 'class WebSocketManager' in text or 'WebSocketManager(' in text
    assert 'WSEnvelope' in text
    assert 'ws_manager = WebSocketManager()' in text
