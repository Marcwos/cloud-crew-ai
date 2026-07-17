"""Tests for application use cases.

Uses FAKES only — no real LLM calls, no real DB, no network.

The sequential `run_crew_session` use case was removed once the LangGraph
graph (`run_graph`) became the single runtime entry point; the crew workflow
is covered by test_langgraph_orchestration.py. What remains here is the rest
of the application surface: get_session, the in-memory repo, and the
recording event publisher.
"""
import pytest

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.application.use_cases.get_session import get_session
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher


@pytest.fixture
def deps() -> CrewSessionDeps:
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )


class TestGetSession:
    async def test_get_existing_session(self, deps):
        saved = CrewSession(
            session_id="get-session-001",
            challenge="Container orchestration strategy",
            constraints=[],
            tasks={},
            proposals=[],
            reviews=[],
            final_plan=None,
            events=[],
        )
        await deps.repo.save(saved)
        retrieved = await get_session(saved.session_id, deps.repo)
        assert retrieved is not None
        assert retrieved.session_id == "get-session-001"

    async def test_get_nonexistent_session_returns_none(self, deps):
        result = await get_session("nonexistent-session-id", deps.repo)
        assert result is None


class TestInMemoryCrewRepository:
    async def test_save_and_get(self, deps):
        from src.features.crew.domain.value_objects.constraint import Constraint

        session = CrewSession(
            session_id="repo-test-001",
            challenge="Test challenge",
            constraints=[Constraint(kind="cost", detail="under $100")],
            tasks={},
            proposals=[],
            reviews=[],
            final_plan=None,
            events=[],
        )
        await deps.repo.save(session)
        retrieved = await deps.repo.get("repo-test-001")
        assert retrieved is not None
        assert retrieved.session_id == "repo-test-001"

    async def test_get_nonexistent_returns_none(self, deps):
        result = await deps.repo.get("does-not-exist")
        assert result is None


class TestRecordingEventPublisher:
    async def test_records_published_events(self, deps):
        from src.features.crew.domain.value_objects.agent_event import AgentEvent

        event = AgentEvent(agent="alan", action="analyzing", status="ok", message="test")
        await deps.events.publish("session-1", event)
        assert len(deps.events.published_events) == 1
        assert deps.events.published_events[0] == ("session-1", event)

    async def test_records_multiple_events(self, deps):
        from src.features.crew.domain.value_objects.agent_event import AgentEvent

        events = [
            AgentEvent(agent="alan", action="idle", status="ok", message="m1"),
            AgentEvent(agent="edgar", action="analyzing", status="ok", message="m2"),
        ]
        for e in events:
            await deps.events.publish("session-1", e)
        assert len(deps.events.published_events) == 2
