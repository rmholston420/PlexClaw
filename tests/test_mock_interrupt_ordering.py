from __future__ import annotations

import asyncio

import pytest

from app import runtime_sdk


@pytest.mark.asyncio
async def test_mock_interrupt_emits_interrupted_and_preserves_session_state() -> None:
    session = await runtime_sdk.create_session(
        runtime_sdk.SessionCreateRequest(
            model="mock-model",
            provider="cloud",
            cwd=".",
            permission_mode="auto",
        )
    )

    emitted: list[str] = []
    original_emit = runtime_sdk._emit

    async def capture_emit(live_session, env) -> None:
        emitted.append(env.type)
        await original_emit(live_session, env)

    runtime_sdk._emit = capture_emit
    try:
        prompt_task = asyncio.create_task(
            runtime_sdk.submit_prompt(session.id, "interrupt me")
        )
        await asyncio.sleep(0.01)
        await runtime_sdk.interrupt_session(session.id)
        await prompt_task
        current = runtime_sdk._sessions[session.id]
        assert current.status == "interrupted"
    finally:
        runtime_sdk._emit = original_emit
        await runtime_sdk.delete_session(session.id)

    assert "session.interrupted" in emitted
    assert "session.failed" not in emitted
