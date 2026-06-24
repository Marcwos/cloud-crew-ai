"""Tests for LangGraph orchestration layer — RED first.

The graph must:
- Run Leslie triage
- Fan out 5 specialists in parallel
- Collect proposals into a fan-in
- Run 1 review round
- Leslie consolidates into a FinalPlan
- Publish AgentEvents at each transition
"""
from __future__ import annotations

import pytest

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.orchestration.langgraph_graph import run_graph


@pytest.fixture
def deps() -> CrewSessionDeps:
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=None,  # type: ignore[arg-type]  # graph doesn't persist
        events=RecordingEventPublisher(),
    )


class TestLangGraphGraph:
    async def test_run_graph_returns_crew_session(self, deps):
        session = await run_graph("Build a serverless pipeline", deps)
        assert isinstance(session, CrewSession)

    async def test_run_graph_has_five_proposals(self, deps):
        session = await run_graph("Real-time data ingestion for IoT", deps)
        assert len(session.proposals) == 5, "Expected one proposal per specialist"

    async def test_run_graph_has_final_plan(self, deps):
        session = await run_graph("Multi-tenant SaaS backend", deps)
        assert session.final_plan is not None
        assert session.final_plan.summary != ""

    async def test_run_graph_has_at_least_one_review(self, deps):
        session = await run_graph("E-commerce backend with high traffic", deps)
        assert len(session.reviews) >= 1

    async def test_run_graph_publishes_events(self, deps):
        await run_graph("Document processing pipeline", deps)
        assert len(deps.events.published_events) > 0

    async def test_run_graph_events_cover_all_agents(self, deps):
        session = await run_graph("API gateway modernization", deps)
        agents_with_events = {e.agent for e in session.events}
        expected = {"leslie", "alan", "edgar", "hedy", "grace", "vint"}
        assert expected.issubset(agents_with_events)

    async def test_run_graph_leslie_first_event(self, deps):
        """Leslie's triage should be the very first event."""
        session = await run_graph("Batch processing job", deps)
        assert session.events[0].agent == "leslie"

    async def test_run_graph_leslie_done_event(self, deps):
        """There must be a leslie 'done' event at the end."""
        session = await run_graph("Video transcoding service", deps)
        leslie_done = [e for e in session.events if e.agent == "leslie" and e.action == "done"]
        assert len(leslie_done) >= 1

    async def test_run_graph_parallel_specialists(self, deps):
        """All 5 specialists should appear in proposals (fan-out happened)."""
        session = await run_graph("Microservices migration", deps)
        proposal_agents = {p.agent for p in session.proposals}
        assert proposal_agents == {"alan", "edgar", "hedy", "grace", "vint"}

    async def test_run_graph_all_proposals_valid(self, deps):
        """Each proposal must have rationale and alternatives."""
        session = await run_graph("Container orchestration", deps)
        for proposal in session.proposals:
            assert proposal.rationale != ""
            assert len(proposal.alternatives_rejected) >= 1
            assert len(proposal.services) >= 1


class TestRunGraphSessionId:
    """run_graph must honour a caller-supplied session_id.

    The route pre-allocates the id returned to the client and the SSE queue is
    keyed by that id. If the graph mints its own id, every event lands in the
    wrong queue and the live stream is empty.
    """

    async def test_run_graph_uses_provided_session_id(self, deps):
        session = await run_graph("Build a serverless pipeline", deps, session_id="fixed-id-123")
        assert session.session_id == "fixed-id-123"

    async def test_run_graph_publishes_under_provided_session_id(self, deps):
        await run_graph("Real-time data ingestion", deps, session_id="fixed-id-456")
        published_ids = {sid for sid, _ in deps.events.published_events}
        assert published_ids == {"fixed-id-456"}

    async def test_run_graph_generates_id_when_omitted(self, deps):
        """Backward compatible: omitting session_id still works."""
        session = await run_graph("Multi-tenant SaaS backend", deps)
        assert isinstance(session.session_id, str)
        assert len(session.session_id) > 0
