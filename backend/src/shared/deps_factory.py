"""Composition root factory — wires ports to adapters.

Call build_deps() to get a CrewSessionDeps ready for use.
In fake/test mode (default), uses in-memory adapters — no external services required.
Real adapters (Anthropic/OpenAI/DeepSeek/Bedrock, SSE) are wired when LLM_PROVIDER is set.
"""
from __future__ import annotations

import os

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository
from src.shared.config import get_llm_provider_name, is_fake_mode


def build_deps(session_id: str | None = None) -> CrewSessionDeps:
    """Build and return a wired set of port dependencies.

    When LLM_PROVIDER is 'fake' (default), returns all-fake adapters.
    When a real provider is configured, returns real LLM + SSE adapters.
    """
    if is_fake_mode():
        return _build_fake_deps()
    return _build_real_deps(session_id=session_id)


def _build_fake_deps() -> CrewSessionDeps:
    """All-fake composition for tests and local development."""
    from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
    from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher

    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )


def _build_real_deps(session_id: str | None = None) -> CrewSessionDeps:
    """Real adapters for production use.

    Uses SSEEventPublisher for live streaming and the configured LLM provider.
    session_id is required when using SSEEventPublisher so the queue is pre-registered.
    """
    from src.features.crew.infrastructure.llm.llm_factory import make_llm_provider
    from src.features.crew.infrastructure.events.sse_event_publisher import SSEEventPublisher

    provider_name = get_llm_provider_name()
    config = {
        "api_key": os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY"),
        "region_name": os.environ.get("AWS_DEFAULT_REGION"),
    }

    llm = make_llm_provider(provider_name, config)
    sse_publisher = SSEEventPublisher()

    return CrewSessionDeps(
        llm=llm,
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=sse_publisher,
    )
