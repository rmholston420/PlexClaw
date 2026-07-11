from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import mock_sdk


def make_client() -> mock_sdk.MockSDKClient:
    return mock_sdk.MockSDKClient(
        SimpleNamespace(
            cwd=None,
            permission_mode="default",
            permission_prompt_tool_name=None,
        )
    )


@pytest.mark.asyncio
async def test_query_handles_queueempty_during_stale_drain(monkeypatch):
    client = make_client()

    class DrainQueue:
        def __init__(self):
            self.calls = 0

        def empty(self):
            return False

        def get_nowait(self):
            self.calls += 1
            raise asyncio.QueueEmpty

    drain_queue = DrainQueue()
    client._response_queue = drain_queue

    produced = {"called": False}

    async def fake_produce():
        produced["called"] = True

    monkeypatch.setattr(client, "_produce_tokens", fake_produce)

    created = {}

    class FakeTask:
        def done(self):
            return False

        def cancel(self):
            return None

        def add_done_callback(self, cb):
            created["callback"] = cb

    def fake_create_task(coro):
        created["coro"] = coro
        return FakeTask()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    await client.query(prompt="hello")

    assert drain_queue.calls == 1
    assert created["coro"].cr_code.co_name == "fake_produce"
    assert callable(created["callback"])

    await created["coro"]


@pytest.mark.asyncio
async def test_close_cancels_and_awaits_running_producer():
    client = make_client()

    class FakeTask:
        def __init__(self):
            self.cancelled = False

        def done(self):
            return False

        def cancel(self):
            self.cancelled = True

        def __await__(self):
            async def _inner():
                raise asyncio.CancelledError
            return _inner().__await__()

    task = FakeTask()
    client._producer_task = task

    await client.close()

    assert task.cancelled is True
    assert await client._response_queue.get() is None


@pytest.mark.asyncio
async def test_produce_tokens_full_text_fallback_and_interrupt(monkeypatch):
    client = make_client()
    client._prompt = ""

    monkeypatch.setattr(mock_sdk, "_MOCK_INTRO", "")
    monkeypatch.setattr(mock_sdk, "_CHUNK_DELAY", 0)
    monkeypatch.setattr(mock_sdk, "_CHUNK_SIZE", 10)

    original_sleep = asyncio.sleep

    async def interrupting_sleep(delay):
        client._interrupted = True
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", interrupting_sleep)

    await client._produce_tokens()

    items = []
    while not client._response_queue.empty():
        items.append(client._response_queue.get_nowait())

    def event_data(item):
        if isinstance(item, dict):
            return item
        for attr in ("data", "raw", "_data", "event"):
            value = getattr(item, attr, None)
            if isinstance(value, dict):
                return value
        if hasattr(item, "model_dump"):
            dumped = item.model_dump()
            if isinstance(dumped, dict):
                return dumped
        raise AssertionError(f"Could not extract event data from {item!r}")

    payloads = [event_data(item) for item in items if item is not None]

    assert payloads[0]["type"] == "content_block_start"
    assert any(p["type"] == "content_block_stop" for p in payloads)
    assert payloads[-1]["type"] == "message_stop"
