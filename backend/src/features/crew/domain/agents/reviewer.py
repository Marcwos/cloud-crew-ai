"""CrossReviewer — crew-level role that generates the real cross-review argument.

Named a role (not a persona) because D2 requires the reviewer/target pair to
emerge from the proposals' content — see design §3.1. A method on
`BaseSpecialistAgent` (e.g. `alan.review()`) would fix `reviewer = self`,
hardcoding half of the pair before the LLM even runs. `CrossReviewer` sees all
five real proposals and lets the LLM pick both.

CrossReviewer produces the Review — the LLM's ARGUMENT. It does NOT decide
whether that argument is a strong conflict; that split ("LLM=argumento /
dominio=conflicto") is enforced by keeping conflict detection out of this
module entirely — see `domain.policies.debate.has_strong_conflict`, invoked
separately after the Review already exists.
"""
from __future__ import annotations

from src.features.crew.domain.agents._parsers import parse_single_line_section
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.ports.llm_provider import LLMMessage, LLMProvider, LLMRequest

_SPECIALIST_AGENTS = ("alan", "edgar", "hedy", "grace", "vint")

_REVIEW_SYSTEM = (
    "You are the crew's cross-reviewer. You read every specialist's proposal and "
    "surface the single strongest disagreement between two of them. "
    "Pick the reviewer and the target from the proposals themselves — never a fixed pair. "
    "Pay special attention to each target's ALTERNATIVES_REJECTED: the strongest "
    "challenge is one that defends a service the target explicitly rejected. "
    "Respond in this exact format:\n"
    "REVIEW:\nREVIEWER: <agent>\nTARGET: <agent>\n"
    "CHALLENGE: <one line, name the concrete service you defend>\n"
    "TRADE_OFF: <one line, the honest trade-off>"
)


class CrossReviewer:
    """Generates the single cross-review argument for a debate round."""

    def __init__(self, llm: LLMProvider, model: str | None = None) -> None:
        self._llm = llm
        # Model id is injected (never hardcoded), same convention as specialists.
        # Defaults to the cheap/fast specialist tier — the review is a short,
        # one-shot judgment, not orchestration (design §7).
        if model is None:
            from src.shared.config import get_specialist_model

            model = get_specialist_model()
        self._model = model

    async def review(self, session: CrewSession, proposals: list[Proposal]) -> Review | None:
        """Produce a Review from the real proposals, or `None` if the LLM's
        output cannot be parsed into a valid reviewer/target pair (R8)."""
        request = LLMRequest(
            model=self._model,
            system=_REVIEW_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=self._build_review_message(session, proposals),
                )
            ],
            max_tokens=300,
        )
        response = await self._llm.complete(request)
        return self._parse_review(response.text, proposals)

    def _build_review_message(self, session: CrewSession, proposals: list[Proposal]) -> str:
        proposals_text = "\n\n".join(
            f"[{p.agent.upper()}]\n"
            f"Services: {', '.join(p.services)}\n"
            f"Rationale: {p.rationale}\n"
            f"Alternatives rejected:\n" + "\n".join(f"- {alt}" for alt in p.alternatives_rejected)
            for p in proposals
        )
        return (
            f"Challenge: {session.challenge}\n\n"
            f"Specialist proposals:\n{proposals_text}\n\n"
            "Choose one reviewer and one target from the specialists above and "
            "produce the strongest cross-review."
        )

    def _parse_review(self, text: str, proposals: list[Proposal]) -> Review | None:
        """Parse REVIEWER/TARGET/CHALLENGE/TRADE_OFF into a Review — or None.

        Deliberately does NOT fabricate a fallback like `_parse_proposal` does
        (design §3.3): a Review is not mandatory the way a Proposal is, so an
        unparseable one simply means no debate happens this round.
        """
        reviewer = parse_single_line_section(text, "REVIEWER").strip().lower()
        target = parse_single_line_section(text, "TARGET").strip().lower()
        challenge = parse_single_line_section(text, "CHALLENGE").strip()
        trade_off = parse_single_line_section(text, "TRADE_OFF").strip()

        if not reviewer or reviewer not in _SPECIALIST_AGENTS:
            return None
        if not target or target not in _SPECIALIST_AGENTS:
            return None
        if reviewer == target:
            return None
        if not challenge:
            return None
        if not any(p.agent == target for p in proposals):
            return None

        if not trade_off:
            # Not an identity field (reviewer/target/challenge are) and the
            # entity does not validate it — a neutral default is safe.
            trade_off = "Trade-off not specified by the reviewer"

        return Review(
            reviewer=reviewer,
            target_agent=target,
            challenge=challenge,
            trade_off=trade_off,
        )
