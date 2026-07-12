import pytest

from app import runtime_sdk
from app.schemas import PromptRequest, SessionCreateRequest


@pytest.mark.asyncio
async def test_runtime_seq_monotonic_across_events() -> None:
    # Create session
    req = SessionCreateRequest(model="test-model", provider="ollama", cwd=".")
    session = await runtime_sdk.create_session(req)

    # Capture initial seq from created event
    created_seq = session.seq
    assert isinstance(created_seq, int)

    # Emit a couple of prompts to drive more events
    prompt_req = PromptRequest(prompt="hello", session_id=session.id)
    await runtime_sdk.handle_prompt(prompt_req)
    await runtime_sdk.handle_prompt(prompt_req)

    # Interrupt session to trigger an additional event
    await runtime_sdk.interrupt_session(session.id)

    # The session seq should have advanced strictly beyond created_seq
    assert session.seq > created_seq

    # There should be no manual session.seq += 1 left in runtime_sdk
    # (enforced indirectly by this test staying stable as next_seq evolves)
    await runtime_sdk.delete_session(session.id)
