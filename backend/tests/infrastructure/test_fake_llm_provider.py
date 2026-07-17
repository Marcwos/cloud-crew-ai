"""Tests for `FakeLLMProvider._pick_canned_response` dispatch — RED first.

Covers R10-R13 (`sdd/real-agent-debate`). These tests target a LIVE bug: the
dispatcher reads `request.messages` (user-controlled text) to decide which
canned response to return, so a user challenge or a re-proposal prompt can
hijack the dispatch of an unrelated agent. The fix (WU1) dispatches ONLY on
`request.system`, most-specific-first.

Every assertion here is content-specific — it must fail if the dispatch logic
is wrong, not merely if something is missing.
"""
from __future__ import annotations

import pytest

from src.features.crew.domain.agents.alan import AlanAgent
from src.features.crew.domain.agents.leslie import _CONSOLIDATE_SYSTEM
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.agents.edgar import EdgarAgent
from src.features.crew.domain.agents.grace import GraceAgent
from src.features.crew.domain.agents.hedy import HedyAgent
from src.features.crew.domain.agents.leslie import LeslieAgent
from src.features.crew.domain.agents.vint import VintAgent
from src.features.crew.domain.ports.llm_provider import LLMMessage, LLMRequest
from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.infrastructure.knowledge.curated_catalog import (
    CuratedCatalogKnowledgeSource,
)
from src.features.crew.infrastructure.llm.fake_llm_provider import (
    _CANNED_RESPONSES,
    _REVIEW_TEMPLATE,
    FakeLLMProvider,
    _pick_canned_response,
)


@pytest.fixture
def knowledge() -> CuratedCatalogKnowledgeSource:
    return CuratedCatalogKnowledgeSource()


@pytest.fixture
def base_session() -> CrewSession:
    return CrewSession(
        session_id="test-fake-dispatch",
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


class TestConsolidateDispatch:
    """R11 — consolidate requests must reach the consolidate canned response.

    Post fake-consolidate-polish, consolidate no longer returns the fixed
    `_CANNED_RESPONSES["leslie_consolidate"]` constant verbatim — it builds a
    response from the real proposals in `request.messages` (see
    `TestConsolidateReflectsDebate` below). What this test still protects is
    the WU1 principle itself: dispatch to the consolidate branch is decided
    ONLY by `request.system`, and the returned text has consolidate's
    SUMMARY/SERVICES/JUSTIFICATION/DIAGRAM_HINT shape, never the review shape.
    """

    def test_consolidate_system_dispatches_to_consolidate_response(self):
        # `_CONSOLIDATE_SYSTEM` contains "reviews" but not "consolidat" — this is
        # exactly what makes the current dispatch fall into the "review" branch.
        request = LLMRequest(
            model="test-model",
            system=_CONSOLIDATE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        "Specialist proposals:\n[ALAN]\nServices: AWS Lambda\n\n"
                        "Cross-reviews:\nNo reviews submitted.\n\n"
                        "Produce the integrated final plan."
                    ),
                )
            ],
        )

        picked = _pick_canned_response(request)

        assert picked != _REVIEW_TEMPLATE
        assert picked.startswith("SUMMARY:")
        assert "SERVICES:" in picked
        assert "JUSTIFICATION:" in picked
        assert "REVIEW:" not in picked
        assert "REVIEWER:" not in picked

    def test_user_text_mentioning_review_or_triage_does_not_hijack_consolidate(self):
        """R10 corollary — even with 'review'/'triage' in the user text, a
        consolidate `request.system` must still dispatch to the consolidate
        shape, never the review or triage canned response.
        """
        request = LLMRequest(
            model="test-model",
            system=_CONSOLIDATE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        "Specialist proposals:\n[ALAN]\nServices: AWS Lambda\n\n"
                        "Cross-reviews:\nThis is a triage review of the proposals.\n\n"
                        "Produce the integrated final plan."
                    ),
                )
            ],
        )

        picked = _pick_canned_response(request)

        assert picked != _REVIEW_TEMPLATE
        assert picked != _CANNED_RESPONSES["leslie_triage"]
        assert picked.startswith("SUMMARY:")


class TestUserChallengeDoesNotHijackDispatch:
    """R10 — the dispatcher must ignore request.messages entirely."""

    def test_challenge_mentioning_review_does_not_hijack_specialist_call(
        self, knowledge: CuratedCatalogKnowledgeSource
    ):
        alan_system = AlanAgent(
            llm=FakeLLMProvider(), knowledge=knowledge, model="test-model"
        ).system_prompt

        # The user's challenge text contains "review" — under the buggy dispatch
        # this hijacks the call and returns _REVIEW_TEMPLATE instead of Alan's
        # own canned proposal.
        request = LLMRequest(
            model="test-model",
            system=alan_system,
            messages=[
                LLMMessage(
                    role="user",
                    content="Challenge: build a code review tool\n\nYour task: propose compute services",
                )
            ],
        )

        picked = _pick_canned_response(request)

        assert picked == _CANNED_RESPONSES["alan"]
        assert picked != _REVIEW_TEMPLATE


class TestReProposalDispatch:
    """R13 — a re-proposal prompt must not fall through to the generic branch."""

    def test_re_proposal_system_for_alan_does_not_return_original_verbatim(
        self, knowledge: CuratedCatalogKnowledgeSource
    ):
        alan_system = AlanAgent(
            llm=FakeLLMProvider(), knowledge=knowledge, model="test-model"
        ).system_prompt
        re_propose_system = (
            alan_system
            + " You are revising your earlier proposal in response to a peer review. "
            "Weigh the challenge honestly: change your recommendation if it is right, "
            "defend it if it is wrong."
        )
        request = LLMRequest(
            model="test-model",
            system=re_propose_system,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        "Peer review challenge: for sustained workloads, Amazon ECS with "
                        "Fargate may offer lower total cost than Lambda."
                    ),
                )
            ],
        )

        picked = _pick_canned_response(request)

        # Must NOT be the original proposal verbatim (that would make R6 —
        # "re-proposal must differ from the original" — structurally
        # unsatisfiable in fake mode) and must NOT be the review template.
        assert picked != _CANNED_RESPONSES["alan"]
        assert picked != _REVIEW_TEMPLATE
        # The re-proposal canned response pivots Alan's recommendation to ECS
        # (design §5.6) — a falsifiable, content-specific expectation.
        assert "SERVICES: Amazon ECS" in picked


class TestConsolidateReflectsDebate:
    """`fake-consolidate-polish` — the consolidate response must be built from
    the REAL (post-debate) proposals passed in `request.messages`, not a
    static canned list. Dispatch itself still goes ONLY through
    `request.system` (protected above); this class covers what the response
    CONTAINS once that branch is picked.
    """

    def _consolidate_request(self, proposals_text: str) -> LLMRequest:
        return LLMRequest(
            model="test-model",
            system=_CONSOLIDATE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        f"Specialist proposals:\n{proposals_text}\n\n"
                        "Cross-reviews:\nNo reviews submitted.\n\n"
                        "Produce the integrated final plan."
                    ),
                )
            ],
        )

    def test_services_reflect_revised_proposal_not_canned_lambda(self):
        proposals_text = (
            "[ALAN]\n"
            "Services: Amazon ECS, AWS Fargate\n"
            "Rationale: Predictable pricing for sustained load.\n"
            "Rejected: AWS Lambda\n"
            "Trade-offs: Higher baseline cost.\n\n"
            "[EDGAR]\n"
            "Services: Amazon DynamoDB\n"
            "Rationale: Single-digit ms latency.\n"
            "Rejected: Amazon RDS\n"
            "Trade-offs: Eventual consistency."
        )

        picked = _pick_canned_response(self._consolidate_request(proposals_text))

        services_line = next(
            line for line in picked.splitlines() if line.startswith("SERVICES:")
        )
        assert "Amazon ECS" in services_line
        assert "AWS Fargate" in services_line
        assert "Amazon DynamoDB" in services_line
        assert "AWS Lambda" not in services_line

    def test_dispatch_by_system_only_review_text_does_not_change_shape(self):
        """Sanity companion to R10: a user text with 'review'/'triage' inside
        the proposals block must not change which branch answers — the
        response must still be consolidate-shaped and reflect the proposals.
        """
        proposals_text = "[ALAN]\nServices: Amazon ECS\nRationale: r\nRejected: x\nTrade-offs: t"
        request = LLMRequest(
            model="test-model",
            system=_CONSOLIDATE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        f"Specialist proposals (triage review notes below):\n{proposals_text}\n\n"
                        "Cross-reviews:\nNo reviews submitted.\n\n"
                        "Produce the integrated final plan."
                    ),
                )
            ],
        )

        picked = _pick_canned_response(request)

        assert picked != _REVIEW_TEMPLATE
        assert picked != _CANNED_RESPONSES["leslie_triage"]
        services_line = next(
            line for line in picked.splitlines() if line.startswith("SERVICES:")
        )
        assert "Amazon ECS" in services_line

    def test_consolidate_response_is_deterministic_for_same_proposals(self):
        proposals_text = "[ALAN]\nServices: Amazon ECS, AWS Fargate\nRationale: r\nRejected: x\nTrade-offs: t"

        picked1 = _pick_canned_response(self._consolidate_request(proposals_text))
        picked2 = _pick_canned_response(self._consolidate_request(proposals_text))

        assert picked1 == picked2


class TestConsolidateReflectsRealProposals:
    """R12 — LeslieAgent.consolidate() under FakeLLMProvider must reflect real proposals."""

    async def test_consolidate_with_five_real_proposals_has_multiple_services(
        self, knowledge: CuratedCatalogKnowledgeSource, base_session: CrewSession
    ):
        fake_llm = FakeLLMProvider()
        specialists = [
            AlanAgent(llm=fake_llm, knowledge=knowledge),
            EdgarAgent(llm=fake_llm, knowledge=knowledge),
            HedyAgent(llm=fake_llm, knowledge=knowledge),
            GraceAgent(llm=fake_llm, knowledge=knowledge),
            VintAgent(llm=fake_llm, knowledge=knowledge),
        ]
        proposals = [await specialist.propose(base_session) for specialist in specialists]

        leslie = LeslieAgent(llm=fake_llm, knowledge=knowledge)
        final_plan = await leslie.consolidate(proposals, reviews=[])

        assert len(final_plan.services) > 1
        assert "AWS Lambda" in final_plan.services
        assert "Amazon DynamoDB" in final_plan.services
        assert final_plan.services != ["AWS App Runner"]


class TestConsolidateReflectsDebateEndToEnd:
    """`fake-consolidate-polish` — end-to-end via `run_graph`: when the fake
    provider's guaranteed conflict (grace -> alan, design §5.6) flips Alan's
    proposal from Lambda to ECS/Fargate, the FinalPlan produced by the SAME
    fake run must show the revised services, not the pre-debate original.
    This exercises the full graph but only reads outcomes — no graph/domain
    code is touched by this change.
    """

    async def test_final_plan_reflects_alans_revised_proposal(self):
        from src.features.crew.application.use_cases.run_crew_session import (
            CrewSessionDeps,
        )
        from src.features.crew.infrastructure.events.recording_publisher import (
            RecordingEventPublisher,
        )
        from src.features.crew.infrastructure.orchestration.langgraph_graph import (
            run_graph,
        )

        deps = CrewSessionDeps(
            llm=FakeLLMProvider(),
            knowledge=CuratedCatalogKnowledgeSource(),
            repo=None,  # type: ignore[arg-type]
            events=RecordingEventPublisher(),
        )

        session = await run_graph("E-commerce backend with high traffic", deps)

        assert session.final_plan is not None
        assert "Amazon ECS" in session.final_plan.services
        assert "AWS Fargate" in session.final_plan.services
