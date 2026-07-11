from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import runtime_sdk as runtime
from app.main import app
from app.schemas import SessionCreateRequest


class DummyClient:
    async def interrupt(self):
        return None

    async def close(self):
        return None


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def force_sdk_available():
    old_available = runtime._SDK_AVAILABLE
    runtime._SDK_AVAILABLE = True
    yield
    runtime._SDK_AVAILABLE = old_available


@pytest.mark.asyncio
async def test_delete_session_removes_live_session():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()

    assert runtime.get_session(session.id) is not None

    await runtime.delete_session(session.id)

    assert runtime.get_session(session.id) is None


@pytest.mark.asyncio
async def test_delete_session_clears_context_and_client():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()
    session.context_files["notes.txt"] = "hello"
    session.pending_approvals["tool-1"] = runtime.PendingApproval(
        tool_id="tool-1",
        tool_name="bash",
        tool_input={"cmd": "pwd"},
    )
    session.pending_approvals["tool-1"].decision = "approve"
    session._context_injected = True

    await runtime.delete_session(session.id)

    assert runtime.get_session(session.id) is None


def test_delete_session_route_404_for_missing(client):
    response = client.delete("/api/sessions/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_route_ok(client):
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()

    response = client.delete(f"/api/sessions/{session.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert runtime.get_session(session.id) is None

@pytest.mark.asyncio
async def test_context_files_inject_once_until_context_changes():
    session = await runtime.create_session(
        SessionCreateRequest(
            model="claude-sonnet-4-5",
            provider="cloud",
            permission_mode="manual",
        )
    )
    session._client = DummyClient()

    runtime.add_context_file(session.id, "notes.txt", "alpha")
    first = runtime._inject_context_into_prompt(session, "hello")
    second = runtime._inject_context_into_prompt(session, "follow-up")

    assert "Attached file context:" in first
    assert "--- FILE: notes.txt ---" in first
    assert "alpha" in first
    assert "--- USER PROMPT ---" in first
    assert first.endswith("hello")

    assert second == "follow-up"

    runtime.add_context_file(session.id, "todo.txt", "beta")
    third = runtime._inject_context_into_prompt(session, "after add")

    assert "Attached file context:" in third
    assert "--- FILE: notes.txt ---" in third
    assert "--- FILE: todo.txt ---" in third
    assert "alpha" in third
    assert "beta" in third
    assert third.endswith("after add")

    runtime.remove_context_file(session.id, "todo.txt")
    fourth = runtime._inject_context_into_prompt(session, "after remove")

    assert "Attached file context:" in fourth
    assert "--- FILE: notes.txt ---" in fourth
    assert "--- FILE: todo.txt ---" not in fourth
    assert "alpha" in fourth
    assert fourth.endswith("after remove")

    await runtime.delete_session(session.id)

