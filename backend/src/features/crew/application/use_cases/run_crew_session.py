"""Composition-root dependency container for the crew workflow.

`CrewSessionDeps` bundles the port implementations the LangGraph
orchestration (`run_graph`) needs, injected at the composition root. The
original sequential `run_crew_session` use case was removed once the graph
became the single runtime entry point; this module now only carries the deps.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.features.crew.domain.ports.llm_provider import LLMProvider
from src.features.crew.domain.ports.knowledge_source import KnowledgeSource
from src.features.crew.domain.ports.crew_repository import CrewRepository
from src.features.crew.domain.ports.event_publisher import EventPublisher


@dataclass
class CrewSessionDeps:
    """All port dependencies for the crew workflow — injected at composition root."""

    llm: LLMProvider
    knowledge: KnowledgeSource
    repo: CrewRepository
    events: EventPublisher
