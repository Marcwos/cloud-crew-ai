"""EventPublisher port — Protocol for streaming AgentEvents to the frontend."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.features.crew.domain.value_objects.agent_event import AgentEvent


@runtime_checkable
class EventPublisher(Protocol):
    """Port: abstracting event publishing. SSE adapter in production; recording adapter in tests."""

    async def publish(self, session_id: str, event: AgentEvent) -> None:
        """Publish an AgentEvent for a given session."""
        ...
