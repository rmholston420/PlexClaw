import pytest

from app.runtime_sdk import (
    LiveSession,
    _maybe_handle_literal_shell_prompt,
    _sessions,
    submit_prompt,
)
from app.websocket_manager import WSEnvelope


class FakeWSManager:
    def __init__(self) -> None:
        self.envelopes: list[WSEnvelope] = []

    async def broadcast(self, envelope: WSEnvelope) -> None:
        self.envelopes.append(envelope)


class DummyClient:
    async def interrupt(self) -> None:
        return None


@pytest.mark.asyncio
async def test_maybe_handle_literal_shell_prompt_pwd_ls_ls_l(tmp_path):
    cwd = tmp_path
    (cwd / "a.txt").write_text("a")
    (cwd / "b.txt").write_text("b")
    (cwd / "subdir").mkdir()

    session = LiveSession(
        id="shell-test",
        model="test-model",
        cwd=str(cwd),
        provider="test-provider",
        permission_mode="auto",
        sdk_permission_mode="default",
        resume_session_id=None,
        fork_session=None,
        mock_mode=True,
    )

    assert _maybe_handle_literal_shell_prompt(session, "pwd") == str(cwd)

    ls_output = _maybe_handle_literal_shell_prompt(session, "ls")
    assert ls_output is not None
    lines = set(ls_output.split("\n"))
    assert {"a.txt", "b.txt", "subdir"}.issubset(lines)

    ls_l_output = _maybe_handle_literal_shell_prompt(session, "ls -l")
    assert ls_l_output is not None
    ls_l_lines = ls_l_output.split("\n")
    assert any(line.endswith("a.txt") for line in ls_l_lines)
    assert any(line.endswith("b.txt") for line in ls_l_lines)
    assert any(line.endswith("subdir") for line in ls_l_lines)


@pytest.mark.asyncio
async def test_submit_prompt_emits_shell_shortcut_events(tmp_path, monkeypatch):
    fake_ws = FakeWSManager()
    monkeypatch.setattr("app.runtime_sdk.ws_manager", fake_ws)

    session = LiveSession(
        id="shell-flow",
        model="test-model",
        cwd=str(tmp_path),
        provider="test-provider",
        permission_mode="auto",
        sdk_permission_mode="default",
        resume_session_id=None,
        fork_session=None,
        mock_mode=True,
    )
    session._client = DummyClient()
    _sessions[session.id] = session

    async def fake_stream_sdk(session_arg, prompt_with_context):
        raise AssertionError("shell shortcut should bypass _stream_sdk")

    monkeypatch.setattr("app.runtime_sdk._stream_sdk", fake_stream_sdk)

    try:
        await submit_prompt(session.id, "pwd")
    finally:
        _sessions.pop(session.id, None)

    text_events = [e for e in fake_ws.envelopes if e.type == "assistant.delta"]
    completed_events = [
        e for e in fake_ws.envelopes if e.type == "assistant.completed"
    ]

    assert any(str(tmp_path) in e.payload.get("text", "") for e in text_events)
    assert completed_events
