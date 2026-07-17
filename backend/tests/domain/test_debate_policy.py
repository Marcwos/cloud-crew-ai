"""Tests for the strong-conflict domain policy (R3) — RED first.

Pure domain: no LLM, no graph, no mocks, no I/O. `service_names.py` normalizes
free-text service mentions against the curated catalog (the single source of
truth); `debate.py` decides whether a review's challenge contests a service the
target already rejected. The matching is deliberately ASYMMETRIC (design §2.4):

- rejected side (`Proposal.alternatives_rejected`, free text written by the LLM,
  never grounding-filtered) -> EXACT match only, never substring;
- challenge side (free text) -> word-boundary match, so a full name or its core
  alias can appear anywhere in a sentence.

Every assertion below is content-specific. If any of these is wrong, the
assertion must fail — not "something is missing".
"""
from __future__ import annotations

from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.policies.debate import (
    find_contested_service,
    has_strong_conflict,
)
from src.features.crew.domain.policies.service_names import (
    build_index,
    canonicalize,
    core_alias,
    mentions,
)
from src.features.crew.infrastructure.knowledge.curated_catalog import (
    CuratedCatalogKnowledgeSource,
)

_COMPUTE_CATALOG = frozenset(
    {
        "AWS Lambda",
        "Amazon ECS",
        "AWS Fargate",
        "Amazon API Gateway",
        "AWS App Runner",
        "Amazon EC2",
    }
)


def _alan_proposal(alternatives_rejected: list[str]) -> Proposal:
    return Proposal(
        agent="alan",
        services=["AWS Lambda", "Amazon API Gateway"],
        rationale="Lambda suits variable-load, event-driven workloads without idle cost.",
        alternatives_rejected=alternatives_rejected,
        trade_offs="Cold-start latency vs zero idle cost",
    )


def _review(challenge: str, reviewer: str = "grace", target_agent: str = "alan") -> Review:
    return Review(
        reviewer=reviewer,
        target_agent=target_agent,
        challenge=challenge,
        trade_off="Lambda flexibility vs predictable pricing for constant load",
    )


class TestCoreAlias:
    """`core_alias` strips a leading vendor prefix — the des-prefijación (design §2.4)."""

    def test_strips_amazon_prefix(self):
        assert core_alias("Amazon ECS") == "ECS"

    def test_strips_aws_prefix(self):
        assert core_alias("AWS X-Ray") == "X-Ray"

    def test_name_without_recognized_prefix_is_unchanged(self):
        assert core_alias("Something Else") == "Something Else"


class TestCanonicalize:
    """EXACT match only (casefold + collapsed whitespace) — never substring."""

    def test_full_name_matches_itself(self):
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("Amazon ECS", index) == "Amazon ECS"

    def test_core_alias_resolves_to_full_canonical_name(self):
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("ECS", index) == "Amazon ECS"

    def test_matching_is_case_insensitive(self):
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("amazon ecs", index) == "Amazon ECS"

    def test_collapses_internal_whitespace(self):
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("Amazon   ECS", index) == "Amazon ECS"

    def test_non_catalog_text_returns_none(self):
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("Self-managed auth", index) is None

    def test_substring_of_a_canonical_name_does_not_canonicalize(self):
        # The known false-positive trap (design §2.4, vint's canned rejection,
        # `fake_llm_provider.py:93`): substring matching would map this to
        # "AWS Lambda" and fabricate a rejection Vint never made.
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("Direct Lambda invocations", index) is None

    def test_qualifier_suffix_is_a_documented_false_negative(self):
        # design §2.4: tolerating suffixes would require fuzzy matching, which
        # kills determinism — this is an accepted, deliberate miss.
        index = build_index(_COMPUTE_CATALOG)
        assert canonicalize("AWS Cost Explorer alone", index) is None


class TestCatalogCoreUniqueness:
    """Invariant (design §2.4, §8 L1): the catalog's canonical names de-prefix
    to unique cores. If a future service collides, `build_index`'s `by_core`
    dict silently drops an entry (last write wins) and matching becomes
    ambiguous — this test must break in red, not fail silently.
    """

    def test_all_catalog_service_cores_are_unique(self):
        catalog_names = frozenset(CuratedCatalogKnowledgeSource().all_service_names())
        index = build_index(catalog_names)

        assert len(catalog_names) == 25
        assert len(index.by_core) == len(catalog_names)


class TestMentions:
    """Word-boundary match (lookarounds, not `\\b`) over {full name, core alias}."""

    def test_full_name_mentioned_in_a_sentence(self):
        index = build_index(_COMPUTE_CATALOG)
        assert mentions("Amazon ECS", "Amazon ECS with Fargate may be cheaper", index) is True

    def test_core_alias_mentioned_in_a_sentence(self):
        index = build_index(_COMPUTE_CATALOG)
        assert mentions("Amazon ECS", "ECS is cheaper for sustained load", index) is True

    def test_ec2_does_not_falsely_match_inside_ecs(self):
        # The EC2/ECS trap (design §2.4): word boundaries must prevent "EC2"
        # from matching as a substring of "ECS".
        index = build_index(_COMPUTE_CATALOG)
        assert mentions("Amazon EC2", "Amazon ECS with Fargate may be cheaper", index) is False

    def test_hyphenated_core_alias_matches_with_lookarounds(self):
        index = build_index(_COMPUTE_CATALOG)
        assert mentions("AWS X-Ray", "We already rely on AWS X-Ray for tracing", index) is True

    def test_unrelated_text_does_not_match(self):
        index = build_index(_COMPUTE_CATALOG)
        assert mentions("Amazon ECS", "Cost-effective microservices architecture", index) is False


class TestFindContestedService:
    """R3 — deterministic conflict detection, no LLM/graph/I-O."""

    def test_conflict_detected_from_canned_alan_and_review_template(self):
        # Mirrors the fake-mode pair (`_CANNED_RESPONSES["alan"]` +
        # `_REVIEW_TEMPLATE`, `fake_llm_provider.py:46-105`): grace challenges
        # alan by naming a service alan explicitly rejected.
        proposal = _alan_proposal(
            [
                "Amazon ECS: Overkill for stateless functions; requires cluster management",
                "Amazon EC2: Fixed cost, manual scaling; not cost-efficient for variable load",
            ]
        )
        review = _review(
            "For sustained workloads, Amazon ECS with Fargate may offer lower total cost "
            "than Lambda with provisioned concurrency. The cold-start mitigation adds cost."
        )

        result = find_contested_service(review, proposal, _COMPUTE_CATALOG)

        assert result == "Amazon ECS"

    def test_no_conflict_when_challenge_names_no_rejected_service(self):
        proposal = _alan_proposal(
            [
                "Amazon ECS: Overkill for stateless functions; requires cluster management",
                "Amazon EC2: Fixed cost, manual scaling; not cost-efficient for variable load",
            ]
        )
        review = _review("AWS App Runner might simplify your deployment pipeline.")

        assert find_contested_service(review, proposal, _COMPUTE_CATALOG) is None

    def test_no_conflict_when_rejected_entry_is_not_in_the_catalog(self):
        proposal = _alan_proposal(["Self-managed auth: High maintenance; security risk"])
        review = _review("You should really consider self-managed auth here.")

        assert find_contested_service(review, proposal, _COMPUTE_CATALOG) is None

    def test_known_false_positive_does_not_trigger(self):
        # The exact guard the asymmetric design exists for: the rejected text
        # is free-form and must NOT canonicalize by substring.
        proposal = _alan_proposal(["Direct Lambda invocations: Tight coupling; no retry guarantees"])
        review = _review("Your team should really use AWS Lambda more.")

        assert find_contested_service(review, proposal, _COMPUTE_CATALOG) is None

    def test_multiple_matches_are_deterministic_first_in_order_wins(self):
        proposal = _alan_proposal(
            [
                "Amazon ECS: Overkill for stateless functions; requires cluster management",
                "Amazon EC2: Fixed cost, manual scaling; not cost-efficient for variable load",
            ]
        )
        review = _review("Both Amazon ECS and Amazon EC2 could handle sustained workloads.")

        assert find_contested_service(review, proposal, _COMPUTE_CATALOG) == "Amazon ECS"

    def test_malformed_rejected_entry_without_colon_is_skipped_not_crashed(self):
        proposal = _alan_proposal(
            [
                "just a note with no colon separator",
                "Amazon ECS: Overkill for stateless functions; requires cluster management",
            ]
        )
        review = _review("Amazon ECS with Fargate looks like the better fit here.")

        assert find_contested_service(review, proposal, _COMPUTE_CATALOG) == "Amazon ECS"


class TestHasStrongConflict:
    """Boolean wrapper over `find_contested_service` — R3's public contract."""

    def test_true_when_a_service_is_contested(self):
        proposal = _alan_proposal(
            ["Amazon ECS: Overkill for stateless functions; requires cluster management"]
        )
        review = _review("Amazon ECS with Fargate may offer lower total cost.")

        assert has_strong_conflict(review, proposal, _COMPUTE_CATALOG) is True

    def test_false_when_no_service_is_contested(self):
        proposal = _alan_proposal(
            ["Amazon ECS: Overkill for stateless functions; requires cluster management"]
        )
        review = _review("AWS App Runner might simplify your deployment pipeline.")

        assert has_strong_conflict(review, proposal, _COMPUTE_CATALOG) is False
