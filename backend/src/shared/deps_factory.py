"""Composition root factory — wires ports to adapters.

Call build_deps() to get a CrewSessionDeps ready for use.
In fake/test mode (default), uses in-memory adapters — no external services required.
Real adapters (Anthropic, PostgreSQL, SSE) will be wired here when LLM_PROVIDER is set.
"""
from __future__ import annotations

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher
from src.shared.config import is_fake_mode


def build_deps() -> CrewSessionDeps:
    """Build and return a wired set of port dependencies.

    Currently always returns fake adapters.
    When LLM_PROVIDER != 'fake', real adapters will be selected here.
    """
    if is_fake_mode():
        return _build_fake_deps()
    # Real adapters stub — extend when implementing real LLM/SSE/DB adapters
    return _build_fake_deps()


def _build_fake_deps() -> CrewSessionDeps:
    """All-fake composition for tests and local development."""
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )
