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
from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource


class HallucinatingLLMProvider:
    """Stub LLM that injects an invented (ungrounded) service into every response.

    Used to prove the grounding filter actually strips services that no
    specialist proposed and no catalog contains.
    """

    INVENTED_SERVICE = "Amazon FooBar"

    def __init__(self) -> None:
        self.received_models: list[str] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.received_models.append(request.model)
        system_lower = request.system.lower()
        messages_text = " ".join(m.content.lower() for m in request.messages)

        if "consolidat" in system_lower or "consolidat" in messages_text:
            text = (
                "SUMMARY: Plan with a hallucinated service injected.\n"
                f"SERVICES: AWS Lambda, {self.INVENTED_SERVICE}\n"
                "JUSTIFICATION:\n"
                "- AWS Lambda: real grounded service\n"
                f"- {self.INVENTED_SERVICE}: invented service that must be stripped\n"
                "DIAGRAM_HINT: Lambda flow\n"
            )
            return LLMResponse(text=text, model=request.model)

        # Specialist proposal path — inject the invented service first.
        text = (
            f"SERVICES: {self.INVENTED_SERVICE}, AWS Lambda\n"
            "RATIONALE: includes an invented service that must be filtered out\n"
            "ALTERNATIVES_REJECTED:\n- Amazon EC2: too heavy\n"
            "TRADE_OFFS: cost vs simplicity\n"
        )
        return LLMResponse(text=text, model=request.model)


class ModelCapturingLLMProvider:
    """Stub LLM that records the model id of every request it receives."""

    def __init__(self) -> None:
        self.received_models: list[str] = []
        self._delegate = FakeLLMProvider()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.received_models.append(request.model)
        return await self._delegate.complete(request)


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


class TestSpecialistGroundingRejection:
    """Blocker 4 — the grounding filter must actively REJECT invented services."""

    async def test_specialist_strips_invented_service(self, knowledge, base_session):
        """A hallucinating LLM proposing 'Amazon FooBar' must NOT reach the Proposal."""
        llm = HallucinatingLLMProvider()
        agent = AlanAgent(llm=llm, knowledge=knowledge)

        proposal = await agent.propose(base_session)

        assert HallucinatingLLMProvider.INVENTED_SERVICE not in proposal.services
        known = await knowledge.services_for("compute", "")
        known_names = {sf.name for sf in known}
        for service in proposal.services:
            assert service in known_names
        # The real grounded service it also proposed survives the filter.
        assert "AWS Lambda" in proposal.services


class TestFinalPlanGrounding:
    """Blocker 1 — Leslie's FinalPlan must be grounded: no invented service can reach the client."""

    async def test_consolidate_strips_invented_service_from_final_plan(self, knowledge):
        """A consolidate LLM output with an invented service must be filtered out."""
        llm = HallucinatingLLMProvider()
        agent = LeslieAgent(llm=llm, knowledge=knowledge)

        proposals = [
            Proposal(
                agent="alan",
                services=["AWS Lambda", "Amazon API Gateway"],
                rationale="Serverless compute",
                alternatives_rejected=["Amazon EC2: heavier"],
                trade_offs="cold start vs idle cost",
            ),
        ]

        final_plan = await agent.consolidate(proposals, [])

        assert HallucinatingLLMProvider.INVENTED_SERVICE not in final_plan.services
        assert (
            HallucinatingLLMProvider.INVENTED_SERVICE
            not in final_plan.justification_by_service
        )
        # Grounded services proposed by specialists survive.
        assert "AWS Lambda" in final_plan.services

    async def test_final_plan_only_contains_grounded_services(self, fake_llm, knowledge):
        """Every service in the FinalPlan must be grounded — proposal union ∪ catalog."""
        agent = LeslieAgent(llm=fake_llm, knowledge=knowledge)

        proposals = [
            Proposal(
                agent="alan",
                services=["AWS Lambda", "Amazon API Gateway"],
                rationale="r",
                alternatives_rejected=["Amazon EC2: heavier"],
                trade_offs="t",
            ),
            Proposal(
                agent="edgar",
                services=["Amazon DynamoDB", "Amazon S3"],
                rationale="r",
                alternatives_rejected=["Amazon RDS: heavier"],
                trade_offs="t",
            ),
        ]
        grounded = {s for p in proposals for s in p.services} | knowledge.all_service_names()

        final_plan = await agent.consolidate(proposals, [])

        for service in final_plan.services:
            assert service in grounded, f"Ungrounded service '{service}' reached the FinalPlan"


class TestFinalPlanEntityGrounding:
    """Blocker 1 — the FinalPlan entity should be able to reject ungrounded services itself."""

    def test_entity_rejects_service_not_in_allowed_set(self):
        with pytest.raises(ValueError, match="not grounded"):
            FinalPlan(
                summary="s",
                services=["AWS Lambda", "Amazon FooBar"],
                justification_by_service={
                    "AWS Lambda": "ok",
                    "Amazon FooBar": "invented",
                },
                diagram_hint="d",
                allowed_services={"AWS Lambda"},
            )

    def test_entity_accepts_grounded_services(self):
        plan = FinalPlan(
            summary="s",
            services=["AWS Lambda"],
            justification_by_service={"AWS Lambda": "ok"},
            diagram_hint="d",
            allowed_services={"AWS Lambda", "Amazon S3"},
        )
        assert plan.services == ["AWS Lambda"]


class TestModelInjection:
    """Blocker 2 — model id must come from config/injection, never hardcoded Claude ids."""

    async def test_specialist_uses_injected_model(self, knowledge, base_session):
        llm = ModelCapturingLLMProvider()
        sentinel = "sentinel-specialist-model"
        agent = AlanAgent(llm=llm, knowledge=knowledge, model=sentinel)

        await agent.propose(base_session)

        assert llm.received_models == [sentinel]

    async def test_leslie_triage_uses_injected_model(self, knowledge):
        llm = ModelCapturingLLMProvider()
        sentinel = "sentinel-orchestrator-model"
        agent = LeslieAgent(llm=llm, knowledge=knowledge, model=sentinel)

        await agent.triage("Build something")

        assert llm.received_models == [sentinel]

    async def test_leslie_consolidate_uses_injected_model(self, knowledge):
        llm = ModelCapturingLLMProvider()
        sentinel = "sentinel-orchestrator-model"
        agent = LeslieAgent(llm=llm, knowledge=knowledge, model=sentinel)

        proposals = [
            Proposal(
                agent="alan",
                services=["AWS Lambda"],
                rationale="r",
                alternatives_rejected=["Amazon EC2: heavier"],
                trade_offs="t",
            ),
        ]
        await agent.consolidate(proposals, [])

        assert llm.received_models == [sentinel]

    async def test_no_hardcoded_claude_model_in_request(self, knowledge, base_session):
        """The model sent must be the injected one, not a hardcoded claude-* literal."""
        llm = ModelCapturingLLMProvider()
        agent = AlanAgent(llm=llm, knowledge=knowledge, model="my-custom-model")

        await agent.propose(base_session)

        assert all(not m.startswith("claude-") for m in llm.received_models)
