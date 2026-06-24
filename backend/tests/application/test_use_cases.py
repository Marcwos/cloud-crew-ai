"""Tests for application use cases — RED first.

Uses FAKES only — no real LLM calls, no real DB, no network.
"""
import pytest

from src.features.crew.application.use_cases.run_crew_session import (
    run_crew_session,
    CrewSessionDeps,
)
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


class TestRunCrewSession:
    async def test_returns_crew_session(self, deps):
        session = await run_crew_session(
            challenge="Build a serverless image processing pipeline",
            deps=deps,
        )
        assert isinstance(session, CrewSession)

    async def test_session_has_proposals(self, deps):
        session = await run_crew_session(
            challenge="Real-time analytics dashboard for 50k users",
            deps=deps,
        )
        assert len(session.proposals) >= 5, "Expected proposals from all 5 specialists"

    async def test_session_has_at_least_one_review(self, deps):
        session = await run_crew_session(
            challenge="E-commerce backend with seasonal traffic spikes",
            deps=deps,
        )
        assert len(session.reviews) >= 1

    async def test_session_has_final_plan(self, deps):
        session = await run_crew_session(
            challenge="Document management system with AI extraction",
            deps=deps,
        )
        assert session.final_plan is not None
        assert session.final_plan.summary != ""
        assert len(session.final_plan.services) >= 1

    async def test_session_has_events(self, deps):
        session = await run_crew_session(
            challenge="IoT data ingestion for 1M devices",
            deps=deps,
        )
        assert len(session.events) > 0

    async def test_session_events_cover_all_agents(self, deps):
        session = await run_crew_session(
            challenge="Multi-tenant SaaS platform",
            deps=deps,
        )
        agents_with_events = {e.agent for e in session.events}
        expected_agents = {"leslie", "alan", "edgar", "hedy", "grace", "vint"}
        assert expected_agents.issubset(agents_with_events)

    async def test_session_is_persisted(self, deps):
        session = await run_crew_session(
            challenge="Serverless data lake ingestion",
            deps=deps,
        )
        retrieved = await deps.repo.get(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    async def test_events_were_published(self, deps):
        await run_crew_session(
            challenge="Real-time fraud detection",
            deps=deps,
        )
        assert len(deps.events.published_events) > 0

    async def test_all_proposals_are_valid(self, deps):
        session = await run_crew_session(
            challenge="Batch video transcoding pipeline",
            deps=deps,
        )
        for proposal in session.proposals:
            assert proposal.rationale != ""
            assert len(proposal.alternatives_rejected) >= 1
            assert len(proposal.services) >= 1

    async def test_final_plan_justification_covers_all_services(self, deps):
        session = await run_crew_session(
            challenge="Microservices migration",
            deps=deps,
        )
        plan = session.final_plan
        assert plan is not None
        for service in plan.services:
            assert service in plan.justification_by_service

    async def test_events_sequence_order(self, deps):
        """Events should follow the expected lifecycle order: leslie starts, leslie ends."""
        session = await run_crew_session(
            challenge="API gateway modernization",
            deps=deps,
        )
        events = session.events
        assert len(events) >= 2
        # Leslie must appear as first agent (triage)
        assert events[0].agent == "leslie"
        # Last event should mark leslie as done (consolidation)
        leslie_done = [e for e in events if e.agent == "leslie" and e.action == "done"]
        assert len(leslie_done) >= 1


class TestGetSession:
    async def test_get_existing_session(self, deps):
        session = await run_crew_session(
            challenge="Container orchestration strategy",
            deps=deps,
        )
        retrieved = await get_session(session.session_id, deps.repo)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

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
