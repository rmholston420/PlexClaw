from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.schemas import PROTOCOL_VERSION


def test_websocket_rejects_missing_protocol_version():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/missing-session"):
            pass

    assert exc.value.code == 4400
    assert "protocol_version mismatch" in str(exc.value.reason)


def test_websocket_rejects_mismatched_protocol_version():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/missing-session?protocol_version=999.0"):
            pass

    assert exc.value.code == 4400
    assert "protocol_version mismatch" in str(exc.value.reason)


def test_websocket_rejects_missing_session_with_valid_protocol():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            f"/ws/missing-session?protocol_version={PROTOCOL_VERSION}"
        ):
            pass

    assert exc.value.code == 4404
    assert "session not found" in str(exc.value.reason)
