"""Tests for domain value objects — RED first."""
import pytest
from pydantic import ValidationError

from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.domain.value_objects.service_fact import ServiceFact
from src.features.crew.domain.value_objects.agent_event import AgentEvent


class TestConstraint:
    def test_valid_cost_constraint(self):
        c = Constraint(kind="cost", detail="Keep monthly bill under $500")
        assert c.kind == "cost"
        assert c.detail == "Keep monthly bill under $500"

    def test_valid_security_constraint(self):
        c = Constraint(kind="security", detail="SOC2 compliance required")
        assert c.kind == "security"

    def test_valid_latency_constraint(self):
        c = Constraint(kind="latency", detail="P99 < 200ms")
        assert c.kind == "latency"

    def test_valid_scale_constraint(self):
        c = Constraint(kind="scale", detail="10k concurrent users")
        assert c.kind == "scale"

    def test_valid_compliance_constraint(self):
        c = Constraint(kind="compliance", detail="GDPR")
        assert c.kind == "compliance"

    def test_invalid_kind_raises(self):
        with pytest.raises(ValidationError):
            Constraint(kind="performance", detail="something")

    def test_constraint_is_frozen(self):
        c = Constraint(kind="cost", detail="under $500")
        with pytest.raises(Exception):
            c.kind = "security"  # type: ignore[misc]

    def test_empty_detail_raises(self):
        with pytest.raises(ValidationError):
            Constraint(kind="cost", detail="")


class TestServiceFact:
    def test_valid_service_fact(self):
        sf = ServiceFact(
            name="AWS Lambda",
            category="compute",
            when_to_use="Event-driven, short-lived, variable workloads",
            source="curated_catalog_v1",
        )
        assert sf.name == "AWS Lambda"
        assert sf.category == "compute"
        assert sf.source == "curated_catalog_v1"

    def test_service_fact_is_frozen(self):
        sf = ServiceFact(
            name="Amazon S3",
            category="data",
            when_to_use="Object storage for any scale",
            source="curated_catalog_v1",
        )
        with pytest.raises(Exception):
            sf.name = "Something else"  # type: ignore[misc]

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ServiceFact(name="", category="compute", when_to_use="x", source="y")

    def test_empty_category_raises(self):
        with pytest.raises(ValidationError):
            ServiceFact(name="Lambda", category="", when_to_use="x", source="y")


class TestAgentEvent:
    def test_valid_agent_event(self):
        e = AgentEvent(
            agent="alan",
            action="analyzing",
            status="in_progress",
            message="Evaluating Lambda vs Fargate",
        )
        assert e.agent == "alan"
        assert e.action == "analyzing"

    def test_all_valid_actions(self):
        for action in ("idle", "moving", "analyzing", "proposing", "reviewing", "done"):
            e = AgentEvent(agent="edgar", action=action, status="ok", message="msg")
            assert e.action == action

    def test_invalid_action_raises(self):
        with pytest.raises(ValidationError):
            AgentEvent(agent="hedy", action="sleeping", status="ok", message="msg")

    def test_agent_event_is_frozen(self):
        e = AgentEvent(agent="grace", action="idle", status="ok", message="msg")
        with pytest.raises(Exception):
            e.agent = "vint"  # type: ignore[misc]

    def test_empty_agent_raises(self):
        with pytest.raises(ValidationError):
            AgentEvent(agent="", action="idle", status="ok", message="msg")
