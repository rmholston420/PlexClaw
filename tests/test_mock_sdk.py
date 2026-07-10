"""Tests for MockSDKClient — verifies mock mode works end-to-end without the real SDK."""

from __future__ import annotations

import asyncio

import pytest

from app.mock_sdk import MockSDKClient, MockStreamEvent


@pytest.mark.asyncio
async def test_mock_client_streams_tokens() -> None:
    client = MockSDKClient(options=None)
    await client.connect()
    await client.query(prompt="hello world")

    events: list[dict] = []
    async for msg in client.receive_response():
        assert isinstance(msg, MockStreamEvent)
        events.append(msg.event)

    types = [e["type"] for e in events]
    assert "content_block_start" in types
    assert "content_block_delta" in types
    assert "content_block_stop" in types
    assert "message_delta" in types
    assert "message_stop" in types


@pytest.mark.asyncio
async def test_mock_client_text_deltas_non_empty() -> None:
    client = MockSDKClient(options=None)
    await client.connect()
    await client.query(prompt="echo this")

    text_chunks: list[str] = []
    async for msg in client.receive_response():
        e = msg.event
        if e.get("type") == "content_block_delta":
            delta = e.get("delta", {})
            if delta.get("type") == "text_delta":
                text_chunks.append(delta["text"])

    assert text_chunks, "Expected at least one text_delta chunk"
    full_text = "".join(text_chunks)
    # The prompt should be echoed inside the response
    assert "echo this" in full_text


@pytest.mark.asyncio
async def test_mock_client_interrupt_stops_stream() -> None:
    client = MockSDKClient(options=None)
    await client.connect()
    # Use a long prompt to guarantee interruption mid-stream
    await client.query(prompt="A" * 2000)

    count = 0
    async for _ in client.receive_response():
        count += 1
        if count == 2:
            await client.interrupt()
            break

    # Just verify interrupt didn't raise
    assert count >= 1


@pytest.mark.asyncio
async def test_mock_client_message_delta_has_stop_reason() -> None:
    client = MockSDKClient(options=None)
    await client.connect()
    await client.query(prompt="test")

    stop_reasons: list[str] = []
    async for msg in client.receive_response():
        e = msg.event
        if e.get("type") == "message_delta":
            delta = e.get("delta", {})
            stop_reasons.append(delta.get("stop_reason", ""))

    assert stop_reasons, "Expected at least one message_delta event"
    assert stop_reasons[-1] == "end_turn"


@pytest.mark.asyncio
async def test_mock_mode_indicator_in_text() -> None:
    """Mock response must contain the mock-mode warning banner."""
    client = MockSDKClient(options=None)
    await client.connect()
    await client.query(prompt="ping")

    chunks: list[str] = []
    async for msg in client.receive_response():
        e = msg.event
        if e.get("type") == "content_block_delta":
            delta = e.get("delta", {})
            if delta.get("type") == "text_delta":
                chunks.append(delta["text"])

    full = "".join(chunks)
    assert "mock mode" in full.lower() or "PlexClaw mock mode" in full
