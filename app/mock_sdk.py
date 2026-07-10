"""Mock SDK driver for PlexClaw.

Used when `claude-agent-sdk` is not installed.  Every session
created in mock mode gets a MockSDKClient that streams a realistic
echo/acknowledgement response through the same normalizer pipeline
used by the real SDK, so the UI receives genuine protocol envelopes.

Mock responses are token-by-token so the streaming UI path is exercised.
"""

from __future__ import annotations

import asyncio
import textwrap
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

_MOCK_INTRO = (
    "\u26a0\ufe0f  **PlexClaw mock mode** — `claude-agent-sdk` is not installed.\n\n"
    "To enable real Claude Code sessions:\n"
    "1. `pip install claude-agent-sdk`\n"
    "2. Set `ANTHROPIC_API_KEY=<your-key>`\n"
    "3. Restart the backend\n\n"
    "---\n\n"
    "**Your prompt (echoed):**\n\n"
)

_CHUNK_SIZE = 6  # characters per token-like chunk
_CHUNK_DELAY = 0.025  # seconds between chunks


class MockSDKClient:
    """Drop-in replacement for ClaudeSDKClient used when the real SDK is absent."""

    def __init__(self, options: Any) -> None:
        self._options = options
        self._prompt: str = ""
        self._interrupted = False
        self._response_queue: asyncio.Queue[str | None] = asyncio.Queue()

    # ------------------------------------------------------------------
    # Interface mirroring ClaudeSDKClient
    # ------------------------------------------------------------------

    async def connect(self) -> None:  # noqa: D401
        """No-op — mock needs no network connection."""
        self._interrupted = False

    async def query(self, *, prompt: str) -> None:
        """Stage the mock response for the given prompt."""
        self._prompt = prompt
        self._interrupted = False
        # Drain any stale items
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        asyncio.create_task(self._produce_tokens())

    async def receive_response(self):  # noqa: ANN201
        """Yield MockStreamEvent objects until sentinel None."""
        while True:
            item = await self._response_queue.get()
            if item is None:
                return
            yield item

    async def interrupt(self) -> None:
        self._interrupted = True
        # Push sentinel to unblock receive_response
        await self._response_queue.put(None)

    async def close(self) -> None:
        await self._response_queue.put(None)

    # ------------------------------------------------------------------
    # Token production
    # ------------------------------------------------------------------

    async def _produce_tokens(self) -> None:
        full_text = _MOCK_INTRO + self._prompt
        tool_id = str(uuid.uuid4())

        # content_block_start (text)
        await self._response_queue.put(
            MockStreamEvent(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
            )
        )

        chunks = textwrap.wrap(full_text, _CHUNK_SIZE, break_long_words=True, break_on_hyphens=False)
        if not chunks and full_text:
            chunks = [full_text]

        for chunk in chunks:
            if self._interrupted:
                break
            await asyncio.sleep(_CHUNK_DELAY)
            await self._response_queue.put(
                MockStreamEvent(
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": chunk},
                    }
                )
            )

        # content_block_stop
        await self._response_queue.put(
            MockStreamEvent({"type": "content_block_stop", "index": 0})
        )

        # message_delta with stop_reason
        await self._response_queue.put(
            MockStreamEvent(
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": len(chunks)},
                }
            )
        )

        # message_stop
        await self._response_queue.put(
            MockStreamEvent({"type": "message_stop"})
        )

        # sentinel
        await self._response_queue.put(None)

        _ = tool_id  # silence unused-variable warning


class MockStreamEvent:
    """Minimal stand-in for claude_agent_sdk.types.StreamEvent."""

    def __init__(self, event: dict) -> None:
        self.event = event

    def __repr__(self) -> str:  # pragma: no cover
        return f"MockStreamEvent({self.event!r})"
