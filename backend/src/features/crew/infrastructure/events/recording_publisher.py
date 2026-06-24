"""RecordingEventPublisher — captures events in a list for test assertions."""
from __future__ import annotations

from src.features.crew.domain.value_objects.agent_event import AgentEvent


class RecordingEventPublisher:
    """Test adapter: records every published (session_id, event) tuple for assertion."""

    def __init__(self) -> None:
        self.published_events: list[tuple[str, AgentEvent]] = []

    async def publish(self, session_id: str, event: AgentEvent) -> None:
        """Record the event — does not push to SSE."""
        self.published_events.append((session_id, event))
