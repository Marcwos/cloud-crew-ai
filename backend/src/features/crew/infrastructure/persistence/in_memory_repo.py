"""InMemoryCrewRepository — in-memory implementation of the CrewRepository port."""
from __future__ import annotations

from src.features.crew.domain.entities.crew_session import CrewSession


class InMemoryCrewRepository:
    """In-memory session store. No DB required — swapped for PostgresRepo later."""

    def __init__(self) -> None:
        self._store: dict[str, CrewSession] = {}

    async def save(self, session: CrewSession) -> None:
        """Persist or overwrite a CrewSession by session_id."""
        self._store[session.session_id] = session

    async def get(self, session_id: str) -> CrewSession | None:
        """Retrieve a CrewSession, or None if not found."""
        return self._store.get(session_id)
