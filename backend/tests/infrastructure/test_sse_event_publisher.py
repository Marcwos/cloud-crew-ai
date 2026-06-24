"""Tests for SSE event publisher — RED first.

The SSEEventPublisher must:
- Implement EventPublisher port (async publish)
- Store events in per-session asyncio.Queue
- Provide an async generator that yields events as SSE-formatted strings
- End the stream when a terminal event (action="done", agent="leslie") is published
"""
from __future__ import annotations

import asyncio
import pytest

from src.features.crew.domain.value_objects.agent_event import AgentEvent
from src.features.crew.infrastructure.events.sse_event_publisher import SSEEventPublisher


@pytest.fixture
def publisher() -> SSEEventPublisher:
    return SSEEventPublisher()


class TestSSEEventPublisher:
    async def test_publish_puts_event_in_queue(self, publisher):
        event = AgentEvent(agent="alan", action="analyzing", status="ok", message="test")
        await publisher.publish("session-1", event)
        queue = publisher.get_queue("session-1")
        assert not queue.empty()

    async def test_get_queue_creates_queue_on_demand(self, publisher):
        queue = publisher.get_queue("session-new")
        assert queue is not None

    async def test_get_queue_is_stable(self, publisher):
        q1 = publisher.get_queue("session-1")
        q2 = publisher.get_queue("session-1")
        assert q1 is q2

    async def test_sse_stream_yields_published_events(self, publisher):
        session_id = "session-stream-1"
        events_to_publish = [
            AgentEvent(agent="alan", action="analyzing", status="ok", message="m1"),
            AgentEvent(agent="leslie", action="done", status="ok", message="done"),
        ]

        async def producer():
            for event in events_to_publish:
                await publisher.publish(session_id, event)

        asyncio.create_task(producer())

        collected = []
        async for data in publisher.event_stream(session_id):
            collected.append(data)
            if len(collected) >= 2:
                break

        assert len(collected) == 2
        assert "alan" in collected[0]
        assert "leslie" in collected[1]

    async def test_sse_stream_ends_after_leslie_done(self, publisher):
        """Stream must terminate after receiving leslie's done event."""
        session_id = "session-stream-2"

        events_sequence = [
            AgentEvent(agent="alan", action="analyzing", status="ok", message="m1"),
            AgentEvent(agent="leslie", action="done", status="ok", message="final"),
        ]

        async def producer():
            await asyncio.sleep(0.01)
            for ev in events_sequence:
                await publisher.publish(session_id, ev)

        asyncio.create_task(producer())

        collected = []
        async for data in publisher.event_stream(session_id):
            collected.append(data)

        # Stream must have ended — we got exactly the 2 events
        assert len(collected) == 2

    async def test_multiple_sessions_isolated(self, publisher):
        """Events for session A must not appear in session B's stream."""
        event_a = AgentEvent(agent="alan", action="analyzing", status="ok", message="A")
        event_b = AgentEvent(agent="edgar", action="proposing", status="ok", message="B")

        await publisher.publish("session-A", event_a)
        await publisher.publish("session-B", event_b)

        q_a = publisher.get_queue("session-A")
        q_b = publisher.get_queue("session-B")

        got_a = await q_a.get()
        got_b = await q_b.get()

        assert got_a.agent == "alan"
        assert got_b.agent == "edgar"

    async def test_publish_event_is_json_serialisable(self, publisher):
        import json

        session_id = "session-json"
        event = AgentEvent(agent="grace", action="reviewing", status="ok", message="checking")

        async def producer():
            await publisher.publish(session_id, event)
            # Send terminal event to close stream
            await publisher.publish(
                session_id,
                AgentEvent(agent="leslie", action="done", status="ok", message="done"),
            )

        asyncio.create_task(producer())

        collected = []
        async for data in publisher.event_stream(session_id):
            # Strip "data: " prefix and newlines from SSE format
            json_str = data.replace("data: ", "").strip()
            parsed = json.loads(json_str)
            collected.append(parsed)

        assert collected[0]["agent"] == "grace"
        assert collected[0]["action"] == "reviewing"

    async def test_terminal_error_event_closes_stream(self, publisher):
        """A leslie/done/error event must also terminate the stream (Blocker 3)."""
        session_id = "session-error-close"

        async def producer():
            await publisher.publish(
                session_id,
                AgentEvent(agent="leslie", action="done", status="error", message="boom"),
            )

        asyncio.create_task(producer())

        collected = []
        async for data in publisher.event_stream(session_id):
            collected.append(data)

        assert len(collected) == 1
        assert "error" in collected[0]

    async def test_event_stream_does_not_hang_forever(self, publisher):
        """With a short idle timeout, a stream with no terminal event must still end."""
        session_id = "session-no-terminal"

        async def producer():
            await publisher.publish(
                session_id,
                AgentEvent(agent="alan", action="analyzing", status="ok", message="m"),
            )
            # No terminal event is ever published.

        asyncio.create_task(producer())

        collected = []
        # Bound at the test level: if the generator hangs, wait_for fails loudly.
        async def drain():
            async for data in publisher.event_stream(session_id, idle_timeout=0.2):
                collected.append(data)

        await asyncio.wait_for(drain(), timeout=5.0)
        assert len(collected) >= 1

    async def test_queue_removed_after_stream_closes(self, publisher):
        """The per-session queue must be cleaned up when the stream ends (no leak)."""
        session_id = "session-cleanup"

        async def producer():
            await publisher.publish(
                session_id,
                AgentEvent(agent="leslie", action="done", status="ok", message="done"),
            )

        asyncio.create_task(producer())

        async for _ in publisher.event_stream(session_id):
            pass

        assert session_id not in publisher._queues
