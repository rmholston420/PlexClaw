from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import mock_sdk


def event_data(item):
    if isinstance(item, dict):
        return item
    for attr in ("data", "raw", "_data", "event"):
        value = getattr(item, attr, None)
        if isinstance(value, dict):
            return value
    raise AssertionError(f"Could not extract event data from {item!r}")


def make_client() -> mock_sdk.MockSDKClient:
    return mock_sdk.MockSDKClient(
        SimpleNamespace(
            cwd=None,
            permission_mode="default",
            permission_prompt_tool_name=None,
        )
    )


class AwaitCancelledTask:
    def __init__(self):
        self.cancel_called = False

    def done(self):
        return False

    def cancel(self):
        self.cancel_called = True

    def add_done_callback(self, cb):
        self.callback = cb

    def __await__(self):
        async def _inner():
            raise asyncio.CancelledError

        return _inner().__await__()


@pytest.mark.asyncio
async def test_query_cancels_existing_task_and_ignores_cancellederror(monkeypatch):
    client = make_client()
    existing = AwaitCancelledTask()
    client._producer_task = existing

    created = {}

    async def fake_produce():
        return None

    monkeypatch.setattr(client, "_produce_tokens", fake_produce)

    class NewTask:
        def add_done_callback(self, cb):
            created["callback"] = cb

    def fake_create_task(coro):
        created["coro"] = coro
        return NewTask()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    await client.query(prompt="hello")

    assert existing.cancel_called is True
    assert created["coro"].cr_code.co_name == "fake_produce"
    assert callable(created["callback"])

    await created["coro"]


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

    created = {}

    async def fake_produce():
        return None

    monkeypatch.setattr(client, "_produce_tokens", fake_produce)

    class NewTask:
        def add_done_callback(self, cb):
            created["callback"] = cb

    def fake_create_task(coro):
        created["coro"] = coro
        return NewTask()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    await client.query(prompt="hello")

    assert drain_queue.calls == 1
    assert created["coro"].cr_code.co_name == "fake_produce"
    await created["coro"]


@pytest.mark.asyncio
async def test_close_cancels_and_awaits_running_producer():
    client = make_client()
    task = AwaitCancelledTask()
    client._producer_task = task

    await client.close()

    assert task.cancel_called is True
    assert await client._response_queue.get() is None


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_produce_tokens_full_text_fallback_hits_chunks_assignment(
    monkeypatch,
):
    client = make_client()
    client._prompt = "hello"

    monkeypatch.setattr(mock_sdk, "_MOCK_INTRO", "")

    class EmptyRange:
        def __call__(self, start, stop=None, step=None):
            return []

    monkeypatch.setattr(mock_sdk, "range", EmptyRange(), raising=False)
    monkeypatch.setattr(mock_sdk, "_CHUNK_DELAY", 0)

    items = []

    async def capture_put(item):
        items.append(item)

    monkeypatch.setattr(client._response_queue, "put", capture_put)

    await client._produce_tokens()

    def event_data(item):
        if isinstance(item, dict):
            return item
        for attr in ("data", "raw", "_data", "event"):
            value = getattr(item, attr, None)
            if isinstance(value, dict):
                return value
        raise AssertionError(f"Could not extract event data from {item!r}")

    dumped = [event_data(item) for item in items if item is not None]
    types = [item["type"] for item in dumped]

    assert "content_block_start" in types
    assert "content_block_delta" in types
    assert "content_block_stop" in types
    assert "message_stop" in types

@pytest.mark.asyncio
async def test_produce_tokens_interrupt_breaks_before_sleep(monkeypatch):
    client = make_client()
    client._prompt = "hello"
    client._interrupted = True

    monkeypatch.setattr(mock_sdk, "_MOCK_INTRO", "")
    monkeypatch.setattr(mock_sdk, "_CHUNK_SIZE", 2)

    sleep_called = {"value": False}

    async def fake_sleep(delay):
        sleep_called["value"] = True

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await client._produce_tokens()

    items = []
    while not client._response_queue.empty():
        items.append(client._response_queue.get_nowait())

    dumped = [event_data(item) for item in items if item is not None]
    types = [item["type"] for item in dumped]

    assert sleep_called["value"] is False
    assert "content_block_start" in types
    assert "content_block_delta" not in types
    assert "content_block_stop" in types
    assert "message_stop" in types
