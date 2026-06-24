"""CrewRepository port — Protocol for session persistence."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.features.crew.domain.entities.crew_session import CrewSession


@runtime_checkable
class CrewRepository(Protocol):
    """Port: abstracting session persistence. In-memory today, PostgreSQL tomorrow."""

    async def save(self, session: CrewSession) -> None:
        """Persist or update a CrewSession."""
        ...

    async def get(self, session_id: str) -> CrewSession | None:
        """Retrieve a CrewSession by ID, or None if not found."""
        ...
