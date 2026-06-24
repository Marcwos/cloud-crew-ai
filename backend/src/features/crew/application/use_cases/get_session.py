"""get_session use case — retrieve a CrewSession by ID."""
from __future__ import annotations

from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.ports.crew_repository import CrewRepository


async def get_session(session_id: str, repo: CrewRepository) -> CrewSession | None:
    """Retrieve a CrewSession by ID. Returns None if not found."""
    return await repo.get(session_id)
