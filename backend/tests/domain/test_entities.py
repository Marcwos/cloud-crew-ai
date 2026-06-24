"""Tests for domain entities — RED first."""
import pytest
from pydantic import ValidationError

from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.entities.final_plan import FinalPlan
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.domain.value_objects.agent_event import AgentEvent


class TestProposal:
    def test_valid_proposal(self):
        p = Proposal(
            agent="alan",
            services=["AWS Lambda", "Amazon API Gateway"],
            rationale="Lambda fits variable load; no idle cost",
            alternatives_rejected=["Amazon ECS — overkill for simple functions"],
            trade_offs="Cold start latency vs cost savings",
        )
        assert p.agent == "alan"
        assert "AWS Lambda" in p.services
        assert p.rationale != ""
        assert len(p.alternatives_rejected) > 0

    def test_empty_rationale_raises(self):
        with pytest.raises(ValidationError):
            Proposal(
                agent="alan",
                services=["AWS Lambda"],
                rationale="",
                alternatives_rejected=["ECS"],
                trade_offs="some trade-off",
            )

    def test_empty_alternatives_rejected_raises(self):
        with pytest.raises(ValidationError):
            Proposal(
                agent="alan",
                services=["AWS Lambda"],
                rationale="Valid rationale here",
                alternatives_rejected=[],
                trade_offs="some trade-off",
            )

    def test_empty_services_raises(self):
        with pytest.raises(ValidationError):
            Proposal(
                agent="alan",
                services=[],
                rationale="Valid rationale here",
                alternatives_rejected=["ECS"],
                trade_offs="some trade-off",
            )

    def test_whitespace_only_rationale_raises(self):
        with pytest.raises(ValidationError):
            Proposal(
                agent="alan",
                services=["AWS Lambda"],
                rationale="   ",
                alternatives_rejected=["ECS"],
                trade_offs="some trade-off",
            )


class TestReview:
    def test_valid_review(self):
        r = Review(
            reviewer="grace",
            target_agent="alan",
            challenge="ECS might be cheaper for sustained workloads",
            trade_off="Lambda cold starts vs ECS steady cost",
        )
        assert r.reviewer == "grace"
        assert r.target_agent == "alan"

    def test_empty_challenge_raises(self):
        with pytest.raises(ValidationError):
            Review(
                reviewer="grace",
                target_agent="alan",
                challenge="",
                trade_off="some trade-off",
            )

    def test_empty_reviewer_raises(self):
        with pytest.raises(ValidationError):
            Review(
                reviewer="",
                target_agent="alan",
                challenge="Valid challenge",
                trade_off="some trade-off",
            )


class TestFinalPlan:
    def test_valid_final_plan(self):
        fp = FinalPlan(
            summary="Serverless architecture for variable load",
            services=["AWS Lambda", "Amazon API Gateway", "Amazon DynamoDB"],
            justification_by_service={
                "AWS Lambda": "Handles variable load without idle cost",
                "Amazon API Gateway": "Managed HTTP endpoint",
                "Amazon DynamoDB": "NoSQL for flexible schema",
            },
            diagram_hint="Lambda behind API Gateway, writing to DynamoDB",
        )
        assert "AWS Lambda" in fp.services
        assert fp.justification_by_service["AWS Lambda"] != ""

    def test_empty_summary_raises(self):
        with pytest.raises(ValidationError):
            FinalPlan(
                summary="",
                services=["AWS Lambda"],
                justification_by_service={"AWS Lambda": "reason"},
                diagram_hint="hint",
            )

    def test_empty_services_raises(self):
        with pytest.raises(ValidationError):
            FinalPlan(
                summary="A plan",
                services=[],
                justification_by_service={},
                diagram_hint="hint",
            )

    def test_missing_justification_for_service_raises(self):
        """Every service must have a justification entry."""
        with pytest.raises(ValidationError):
            FinalPlan(
                summary="A plan",
                services=["AWS Lambda", "Amazon S3"],
                justification_by_service={"AWS Lambda": "reason"},
                diagram_hint="hint",
            )


class TestCrewSession:
    def _make_proposal(self, agent: str) -> Proposal:
        return Proposal(
            agent=agent,
            services=["AWS Lambda"],
            rationale="Valid rationale",
            alternatives_rejected=["ECS — overkill"],
            trade_offs="cold start vs cost",
        )

    def test_valid_crew_session(self):
        session = CrewSession(
            session_id="sess-001",
            challenge="Build a file processing pipeline",
            constraints=[Constraint(kind="cost", detail="under $200/mo")],
            tasks={"alan": "Define compute strategy"},
            proposals=[self._make_proposal("alan")],
            reviews=[],
            final_plan=None,
            events=[],
        )
        assert session.session_id == "sess-001"
        assert len(session.proposals) == 1

    def test_empty_session_id_raises(self):
        with pytest.raises(ValidationError):
            CrewSession(
                session_id="",
                challenge="Build something",
                constraints=[],
                tasks={},
                proposals=[],
                reviews=[],
                final_plan=None,
                events=[],
            )

    def test_empty_challenge_raises(self):
        with pytest.raises(ValidationError):
            CrewSession(
                session_id="sess-001",
                challenge="",
                constraints=[],
                tasks={},
                proposals=[],
                reviews=[],
                final_plan=None,
                events=[],
            )

    def test_session_with_events(self):
        event = AgentEvent(agent="leslie", action="analyzing", status="ok", message="Triaging")
        session = CrewSession(
            session_id="sess-002",
            challenge="E-commerce backend",
            constraints=[],
            tasks={},
            proposals=[],
            reviews=[],
            final_plan=None,
            events=[event],
        )
        assert len(session.events) == 1
        assert session.events[0].agent == "leslie"
