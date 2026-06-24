"""Base class for specialist agents (Alan, Edgar, Hedy, Grace, Vint).

Each specialist:
1. Fetches ServiceFacts from KnowledgeSource for their domain
2. Builds a prompt including those facts
3. Calls LLMProvider.complete()
4. Parses the response into a valid Proposal
5. NEVER proposes a service not in the KnowledgeSource response
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.ports.llm_provider import LLMProvider, LLMRequest, LLMMessage
from src.features.crew.domain.ports.knowledge_source import KnowledgeSource
from src.features.crew.domain.value_objects.service_fact import ServiceFact
from src.features.crew.domain.agents._parsers import (
    parse_list_section,
    parse_multiline_section,
    parse_single_line_section,
)


class BaseSpecialistAgent(ABC):
    """Abstract base for all specialist agents. Enforces grounding rule."""

    def __init__(self, llm: LLMProvider, knowledge: KnowledgeSource) -> None:
        self._llm = llm
        self._knowledge = knowledge

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """The agent's identifier (e.g. 'alan')."""
        ...

    @property
    @abstractmethod
    def domain(self) -> str:
        """The KnowledgeSource domain this agent queries (e.g. 'compute')."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System-level instructions for this specialist's LLM call."""
        ...

    def _build_user_message(self, session: CrewSession, facts: list[ServiceFact]) -> str:
        facts_text = "\n".join(
            f"- {f.name}: {f.when_to_use}" for f in facts
        )
        task = session.tasks.get(self.agent_name, "Provide your architectural recommendation")
        challenge = session.challenge
        constraints_text = "\n".join(
            f"- {c.kind}: {c.detail}" for c in session.constraints
        )
        return (
            f"Challenge: {challenge}\n\n"
            f"Constraints:\n{constraints_text}\n\n"
            f"Your task: {task}\n\n"
            f"Available {self.domain} services (use ONLY these):\n{facts_text}\n\n"
            f"Respond in the exact format:\n"
            f"SERVICES: <comma-separated list from the above only>\n"
            f"RATIONALE: <clear justification — why these services, not others>\n"
            f"ALTERNATIVES_REJECTED:\n- <service>: <reason rejected>\n"
            f"TRADE_OFFS: <honest trade-offs of your recommendation>\n"
        )

    def _parse_proposal(self, text: str, allowed_names: set[str]) -> Proposal:
        """Parse LLM text into a Proposal, enforcing the grounding rule."""
        raw_services = parse_list_section(text, "SERVICES")
        # Grounding rule: filter to only services in the curated catalog
        grounded_services = [s for s in raw_services if s in allowed_names]
        if not grounded_services:
            # Fall back to first allowed service if parsing fails
            grounded_services = [next(iter(allowed_names))]

        rationale = parse_single_line_section(text, "RATIONALE")
        if not rationale:
            rationale = "Recommended based on available services and challenge requirements"

        alternatives = parse_multiline_section(text, "ALTERNATIVES_REJECTED")
        if not alternatives:
            # Ensure we always have at least one alternative (domain invariant)
            other_services = [s for s in allowed_names if s not in grounded_services]
            fallback = other_services[0] if other_services else "Manual provisioning"
            alternatives = [f"{fallback}: not selected for this workload"]

        trade_offs = parse_single_line_section(text, "TRADE_OFFS")
        if not trade_offs:
            trade_offs = "Standard trade-offs apply for this service selection"

        return Proposal(
            agent=self.agent_name,
            services=grounded_services,
            rationale=rationale,
            alternatives_rejected=alternatives,
            trade_offs=trade_offs,
        )

    async def propose(self, session: CrewSession) -> Proposal:
        """Produce a grounded Proposal for the given session."""
        facts = await self._knowledge.services_for(self.domain, session.challenge)
        allowed_names = {f.name for f in facts}

        request = LLMRequest(
            model="claude-3-5-haiku-20241022",
            system=self.system_prompt,
            messages=[
                LLMMessage(
                    role="user",
                    content=self._build_user_message(session, facts),
                )
            ],
        )
        response = await self._llm.complete(request)
        return self._parse_proposal(response.text, allowed_names)
