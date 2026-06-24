"""KnowledgeSource port — Protocol for AWS service knowledge retrieval."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.features.crew.domain.value_objects.service_fact import ServiceFact


@runtime_checkable
class KnowledgeSource(Protocol):
    """Port: abstracting the source of truth about AWS services.

    Today: curated catalog. Tomorrow: RAG over docs.
    """

    async def services_for(self, domain: str, need: str) -> list[ServiceFact]:
        """Return relevant ServiceFacts for a given domain and need description."""
        ...
