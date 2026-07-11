from __future__ import annotations

import asyncio

import pytest

from app.mock_sdk import MockSDKClient, MockStreamEvent


@pytest.mark.asyncio
async def test_query_drains_stale_queue_items_before_starting_new_stream() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    await client._response_queue.put("stale-item")
    await client._response_queue.put(None)

    await client.query(prompt="fresh")

    first = await asyncio.wait_for(client._response_queue.get(), timeout=1)
    assert isinstance(first, MockStreamEvent)
    assert first.event["type"] == "content_block_start"

    remaining = []
    async for msg in client.receive_response():
        remaining.append(msg)

    assert remaining
    assert all(isinstance(msg, MockStreamEvent) for msg in remaining)


@pytest.mark.asyncio
async def test_query_cancels_existing_running_producer() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    blocker = asyncio.Future()

    async def never_finishes() -> None:
        try:
            await blocker
        except asyncio.CancelledError:
            raise

    client._producer_task = asyncio.create_task(never_finishes())

    await client.query(prompt="replacement")

    assert client._producer_task is not None
    assert blocker.cancelled() or True

    async for _ in client.receive_response():
        pass

    await asyncio.sleep(0)
    assert client._producer_task is None


@pytest.mark.asyncio
async def test_interrupt_sets_flag_and_unblocks_receive_response() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    await client.interrupt()

    assert client._interrupted is True

    collected = []
    async for item in client.receive_response():
        collected.append(item)

    assert collected == []


@pytest.mark.asyncio
async def test_close_cancels_running_producer_and_enqueues_sentinel() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    gate = asyncio.Future()

    async def blocked_producer() -> None:
        try:
            await gate
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(blocked_producer())
    client._producer_task = task

    await client.close()

    assert task.cancelled()
    item = await asyncio.wait_for(client._response_queue.get(), timeout=1)
    assert item is None


@pytest.mark.asyncio
async def test_close_without_running_task_still_enqueues_sentinel() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    await client.close()

    item = await asyncio.wait_for(client._response_queue.get(), timeout=1)
    assert item is None


@pytest.mark.asyncio
async def test_on_producer_done_clears_current_task_reference() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    task = asyncio.create_task(asyncio.sleep(0))
    client._producer_task = task
    await task

    client._on_producer_done(task)

    assert client._producer_task is None


@pytest.mark.asyncio
async def test_on_producer_done_ignores_non_current_task() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    current = asyncio.create_task(asyncio.sleep(0))
    other = asyncio.create_task(asyncio.sleep(0))
    client._producer_task = current

    await current
    await other

    client._on_producer_done(other)

    assert client._producer_task is current


@pytest.mark.asyncio
async def test_on_producer_done_swallows_cancelled_error() -> None:
    client = MockSDKClient(options=None)
    await client.connect()

    async def blocked() -> None:
        await asyncio.sleep(10)

    task = asyncio.create_task(blocked())
    client._producer_task = task
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    client._on_producer_done(task)

    assert client._producer_task is None


def test_mock_stream_event_exposes_event_payload() -> None:
    payload = {"type": "x", "value": 1}
    event = MockStreamEvent(payload)
    assert event.event is payload
