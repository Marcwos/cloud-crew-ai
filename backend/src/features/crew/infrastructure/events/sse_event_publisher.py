"""SSEEventPublisher — asyncio.Queue-backed EventPublisher adapter.

Each session gets its own asyncio.Queue. The SSE endpoint calls
event_stream(session_id) to receive an async generator that yields
SSE-formatted strings. The stream terminates when leslie emits a "done" event.
"""
from __future__ import annotations

import asyncio
import json

from src.features.crew.domain.value_objects.agent_event import AgentEvent

# Sentinel to signal stream closure
_STREAM_CLOSE = object()

# Default idle timeout (seconds): if no event arrives for this long the stream
# closes instead of blocking forever. Guards against a crashed producer that
# never publishes a terminal event.
_DEFAULT_IDLE_TIMEOUT = 120.0


class SSEEventPublisher:
    """Adapter: publishes AgentEvents into per-session asyncio queues.

    Provides:
    - publish(session_id, event) — called by the use case / graph nodes
    - event_stream(session_id)   — async generator consumed by the SSE route
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def get_queue(self, session_id: str) -> asyncio.Queue:
        """Return (or create) the queue for a session."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    async def publish(self, session_id: str, event: AgentEvent) -> None:
        """Put an event into the session's queue.

        If this is leslie's terminal 'done' event, also enqueue the sentinel
        so the stream generator can exit cleanly.
        """
        queue = self.get_queue(session_id)
        await queue.put(event)

        if event.agent == "leslie" and event.action == "done":
            await queue.put(_STREAM_CLOSE)

    async def event_stream(
        self,
        session_id: str,
        idle_timeout: float = _DEFAULT_IDLE_TIMEOUT,
    ):
        """Async generator yielding SSE-formatted strings for a session.

        Yields strings like: 'data: {"agent": "alan", ...}\n\n'
        Terminates after the stream-close sentinel is dequeued, or when no event
        arrives within ``idle_timeout`` seconds (so a crashed producer that never
        sends a terminal event cannot hang the client forever).

        The per-session queue is removed when the stream closes to avoid leaking
        one queue per session for the lifetime of the process.
        """
        queue = self.get_queue(session_id)

        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=idle_timeout)
                except asyncio.TimeoutError:
                    # No event within the idle window — close instead of hanging.
                    break

                if item is _STREAM_CLOSE:
                    break

                event: AgentEvent = item
                payload = json.dumps(event.model_dump())
                yield f"data: {payload}\n\n"
        finally:
            # Memory-leak fix: drop the queue once the stream is done with it.
            self._queues.pop(session_id, None)
