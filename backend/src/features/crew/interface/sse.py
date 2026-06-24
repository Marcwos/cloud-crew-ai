"""SSE streaming endpoint helpers."""
from __future__ import annotations

import asyncio
import json

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.infrastructure.events.sse_event_publisher import SSEEventPublisher


async def _session_events_from_repo(session: CrewSession):
    """Yield stored events from a completed session as SSE strings.

    Used in test / fake mode where SSEEventPublisher is not wired.
    Emits all events then closes.
    """
    for event in session.events:
        payload = json.dumps(event.model_dump())
        yield f"data: {payload}\n\n"


async def stream_session_events(
    session: CrewSession,
    publisher: object,
) -> StreamingResponse:
    """Build an SSE StreamingResponse for a session.

    If the publisher is an SSEEventPublisher, use its async generator.
    Otherwise (e.g. RecordingPublisher in tests), replay stored events.
    """
    if isinstance(publisher, SSEEventPublisher):
        generator = publisher.event_stream(session.session_id)
    else:
        # Fall back to replaying stored events (test / recording publisher mode)
        generator = _session_events_from_repo(session)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
