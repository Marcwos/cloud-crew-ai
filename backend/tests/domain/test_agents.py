"""Tests for domain agent rules — RED first.

Uses FAKES only — no real LLM calls.
"""
import pytest

from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.final_plan import FinalPlan
from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.domain.agents.leslie import LeslieAgent
from src.features.crew.domain.agents.alan import AlanAgent
from src.features.crew.domain.agents.edgar import EdgarAgent
from src.features.crew.domain.agents.hedy import HedyAgent
from src.features.crew.domain.agents.grace import GraceAgent
from src.features.crew.domain.agents.vint import VintAgent
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def knowledge() -> CuratedCatalogKnowledgeSource:
    return CuratedCatalogKnowledgeSource()


@pytest.fixture
def base_session() -> CrewSession:
    return CrewSession(
        session_id="test-001",
        challenge="Build a document processing pipeline that scales on demand",
        constraints=[
            Constraint(kind="cost", detail="Under $300/month"),
            Constraint(kind="scale", detail="Handle bursts up to 1000 docs/minute"),
        ],
        tasks={
            "alan": "Define compute and API strategy",
            "edgar": "Define storage and database strategy",
            "hedy": "Define security and access control",
            "grace": "Define monitoring and cost optimization",
            "vint": "Define networking and event routing",
        },
        proposals=[],
        reviews=[],
        final_plan=None,
        events=[],
    )


class TestLeslieAgent:
    async def test_triage_produces_constraints_and_tasks(self, fake_llm, knowledge):
        agent = LeslieAgent(llm=fake_llm, knowledge=knowledge)
        challenge = "Build a real-time chat application for 10k concurrent users"
        constraints, tasks = await agent.triage(challenge)

        assert isinstance(constraints, list)
        assert len(constraints) >= 1
        assert isinstance(tasks, dict)
        assert len(tasks) >= 1
        # All agents should have tasks
        for agent_name in ("alan", "edgar", "hedy", "grace", "vint"):
            assert agent_name in tasks
            assert tasks[agent_name] != ""

    async def test_triage_constraints_are_valid(self, fake_llm, knowledge):
        agent = LeslieAgent(llm=fake_llm, knowledge=knowledge)
        constraints, _ = await agent.triage("Build an e-commerce site")
        for c in constraints:
            assert isinstance(c, Constraint)

    async def test_consolidate_produces_final_plan(self, fake_llm, knowledge, base_session):
        # Add some proposals and reviews first
        proposal = Proposal(
            agent="alan",
            services=["AWS Lambda", "Amazon API Gateway"],
            rationale="Serverless is cost-effective for variable load",
            alternatives_rejected=["Amazon ECS — heavier setup for simple case"],
            trade_offs="Cold starts vs no idle cost",
        )
        base_session.proposals.append(proposal)

        agent = LeslieAgent(llm=fake_llm, knowledge=knowledge)
        final_plan = await agent.consolidate(base_session.proposals, base_session.reviews)

        assert isinstance(final_plan, FinalPlan)
        assert final_plan.summary != ""
        assert len(final_plan.services) >= 1
        assert len(final_plan.justification_by_service) >= 1
        # All services must have justification
        for service in final_plan.services:
            assert service in final_plan.justification_by_service


class TestAlanAgent:
    async def test_produces_valid_proposal(self, fake_llm, knowledge, base_session):
        agent = AlanAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        assert isinstance(proposal, Proposal)
        assert proposal.agent == "alan"
        assert proposal.rationale != ""
        assert len(proposal.alternatives_rejected) >= 1
        assert len(proposal.services) >= 1

    async def test_proposal_uses_only_known_services(self, fake_llm, knowledge, base_session):
        """Agent must never invent a service not returned by KnowledgeSource."""
        agent = AlanAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        known = await knowledge.services_for("compute", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names, (
                f"Service '{service}' not in curated catalog for compute domain"
            )

    async def test_proposal_has_compute_services(self, fake_llm, knowledge, base_session):
        agent = AlanAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)
        # Alan deals with compute — at least one compute service expected
        compute_services = {
            "AWS Lambda", "Amazon ECS", "AWS Fargate",
            "Amazon API Gateway", "AWS App Runner", "Amazon EC2",
        }
        assert any(s in compute_services for s in proposal.services)


class TestEdgarAgent:
    async def test_produces_valid_proposal(self, fake_llm, knowledge, base_session):
        agent = EdgarAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        assert isinstance(proposal, Proposal)
        assert proposal.agent == "edgar"
        assert proposal.rationale != ""
        assert len(proposal.alternatives_rejected) >= 1

    async def test_proposal_uses_only_known_services(self, fake_llm, knowledge, base_session):
        agent = EdgarAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        known = await knowledge.services_for("data", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names


class TestHedyAgent:
    async def test_produces_valid_proposal(self, fake_llm, knowledge, base_session):
        agent = HedyAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        assert isinstance(proposal, Proposal)
        assert proposal.agent == "hedy"
        assert proposal.rationale != ""
        assert len(proposal.alternatives_rejected) >= 1

    async def test_proposal_uses_only_known_services(self, fake_llm, knowledge, base_session):
        agent = HedyAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        known = await knowledge.services_for("security", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names


class TestGraceAgent:
    async def test_produces_valid_proposal(self, fake_llm, knowledge, base_session):
        agent = GraceAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        assert isinstance(proposal, Proposal)
        assert proposal.agent == "grace"
        assert proposal.rationale != ""
        assert len(proposal.alternatives_rejected) >= 1

    async def test_proposal_uses_only_known_services(self, fake_llm, knowledge, base_session):
        agent = GraceAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        known = await knowledge.services_for("monitoring_cost", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names


class TestVintAgent:
    async def test_produces_valid_proposal(self, fake_llm, knowledge, base_session):
        agent = VintAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        assert isinstance(proposal, Proposal)
        assert proposal.agent == "vint"
        assert proposal.rationale != ""
        assert len(proposal.alternatives_rejected) >= 1

    async def test_proposal_uses_only_known_services(self, fake_llm, knowledge, base_session):
        agent = VintAgent(llm=fake_llm, knowledge=knowledge)
        proposal = await agent.propose(base_session)

        known = await knowledge.services_for("networking", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names
