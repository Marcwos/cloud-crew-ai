"""Tests for CrossReviewer (R1, R2, R8) — RED first.

Uses a stub LLM — no real API calls. `CrossReviewer` produces the Review, i.e.
the LLM's ARGUMENT. It does NOT decide whether that argument is a strong
conflict — that split ("LLM=argumento / dominio=conflicto") lives in
`domain/policies/debate.py`, exercised separately in `test_debate_policy.py`,
and is invoked later by the graph (WU5), not here.
"""
from __future__ import annotations

import pytest

from src.features.crew.domain.agents.reviewer import CrossReviewer
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider


class StubReviewLLM:
    """Returns a fixed review text regardless of the prompt — records every request sent."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.received_requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.received_requests.append(request)
        return LLMResponse(text=self._text, model=request.model)


def _proposal(agent: str, alternatives_rejected: list[str] | None = None) -> Proposal:
    return Proposal(
        agent=agent,
        services=["AWS Lambda"],
        rationale="Because it fits the workload.",
        alternatives_rejected=alternatives_rejected or ["Amazon EC2: too heavy"],
        trade_offs="Trade-off noted.",
    )


def _all_five_proposals() -> list[Proposal]:
    return [_proposal(name) for name in ("alan", "edgar", "hedy", "grace", "vint")]


@pytest.fixture
def session() -> CrewSession:
    return CrewSession(
        session_id="test-review-001",
        challenge="Build a real-time analytics pipeline",
        constraints=[],
        tasks={},
        proposals=[],
        reviews=[],
        final_plan=None,
        events=[],
    )


class TestCrossReviewerParsing:
    async def test_parses_reviewer_target_challenge_trade_off_into_review(self, session):
        text = (
            "REVIEW:\n"
            "REVIEWER: hedy\n"
            "TARGET: edgar\n"
            "CHALLENGE: Amazon RDS handles compliance auditing better than DynamoDB here.\n"
            "TRADE_OFF: RDS's operational overhead vs DynamoDB's hands-off scaling\n"
        )
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review == Review(
            reviewer="hedy",
            target_agent="edgar",
            challenge="Amazon RDS handles compliance auditing better than DynamoDB here.",
            trade_off="RDS's operational overhead vs DynamoDB's hands-off scaling",
        )

    async def test_blank_trade_off_gets_a_neutral_default_not_a_none_review(self, session):
        """Design §3.3's single concession: TRADE_OFF is not an identity field
        (reviewer/target/challenge are) and `Review` does not validate it, so a
        blank value degrades to neutral text instead of discarding the review."""
        text = "REVIEW:\nREVIEWER: hedy\nTARGET: edgar\nCHALLENGE: DynamoDB lacks the compliance audit trail RDS has.\n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is not None
        assert review.trade_off == "Trade-off not specified by the reviewer"

    async def test_pair_is_not_hardcoded_to_grace_and_alan(self, session):
        """Kills the grace->alan hardcode this WU replaces (design §3.1, D2).

        Mirrors the intent of `test_langgraph_orchestration.py:47-49`, which
        only asserted `len(session.reviews) >= 1` and never verified WHO
        reviewed WHOM — that assertion protected nothing against a hardcoded
        pair. This one does.
        """
        text = (
            "REVIEW:\n"
            "REVIEWER: vint\n"
            "TARGET: edgar\n"
            "CHALLENGE: Amazon SQS decouples this better than the current DynamoDB stream approach.\n"
            "TRADE_OFF: SQS operational simplicity vs DynamoDB Streams' native integration\n"
        )
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is not None
        assert review.reviewer == "vint"
        assert review.target_agent == "edgar"


class TestCrossReviewerReferencesRealProposals:
    async def test_review_message_includes_target_alternatives_rejected(self, session):
        """The generated request must carry the REAL proposal content, not a
        fixed template — the LLM cannot defend a service a target never rejected
        if it never sees what was rejected."""
        proposals = [
            _proposal("alan", alternatives_rejected=["Amazon ECS: Overkill for stateless functions"]),
            _proposal("edgar"),
            _proposal("hedy"),
            _proposal("grace"),
            _proposal("vint"),
        ]
        text = (
            "REVIEW:\nREVIEWER: grace\nTARGET: alan\n"
            "CHALLENGE: Amazon ECS with Fargate is cheaper for sustained load.\n"
            "TRADE_OFF: predictable pricing vs Lambda's zero idle cost\n"
        )
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        await reviewer.review(session, proposals)

        sent_message = llm.received_requests[0].messages[0].content
        assert "Amazon ECS: Overkill for stateless functions" in sent_message
        assert "AWS Lambda" in sent_message  # alan's actual proposed service


class TestCrossReviewerDefensiveFallback:
    """R8 — malformed review output degrades safely: None, never an exception."""

    async def test_none_when_reviewer_equals_target(self, session):
        text = "REVIEW:\nREVIEWER: alan\nTARGET: alan\nCHALLENGE: self-review makes no sense\nTRADE_OFF: n/a\n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is None

    async def test_none_when_target_has_no_proposal_in_state(self, session):
        text = "REVIEW:\nREVIEWER: alan\nTARGET: edgar\nCHALLENGE: DynamoDB is the wrong call.\nTRADE_OFF: n/a\n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)
        proposals_without_edgar = [_proposal("alan"), _proposal("hedy"), _proposal("grace"), _proposal("vint")]

        review = await reviewer.review(session, proposals_without_edgar)

        assert review is None

    async def test_none_when_target_is_an_unknown_agent_name(self, session):
        text = "REVIEW:\nREVIEWER: alan\nTARGET: dexter\nCHALLENGE: not a real agent\nTRADE_OFF: n/a\n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is None

    async def test_none_when_reviewer_is_an_unknown_agent_name(self, session):
        text = "REVIEW:\nREVIEWER: dexter\nTARGET: alan\nCHALLENGE: not a real agent\nTRADE_OFF: n/a\n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is None

    async def test_none_when_challenge_is_blank(self, session):
        # CHALLENGE trails with no value and no further header — a genuinely
        # blank field, not a mid-text blank line (`parse_single_line_section`'s
        # `\s*` would otherwise bleed across the newline into the next header).
        text = "REVIEW:\nREVIEWER: alan\nTARGET: edgar\nCHALLENGE: \n"
        llm = StubReviewLLM(text)
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is None

    async def test_none_does_not_raise_on_completely_unparseable_text(self, session):
        llm = StubReviewLLM("I refuse to follow the format today.")
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is None


class TestCrossReviewerDispatchIntegration:
    """Confirms the system prompt matches `FakeLLMProvider`'s dispatch discriminator
    (design §5.5 — the literal "cross-reviewer" phrase identifies the review branch)."""

    async def test_review_under_fake_llm_provider_returns_the_canned_pair(self, session):
        llm = FakeLLMProvider()
        reviewer = CrossReviewer(llm=llm)

        review = await reviewer.review(session, _all_five_proposals())

        assert review is not None
        assert review.reviewer == "grace"
        assert review.target_agent == "alan"
        assert "Amazon ECS" in review.challenge
