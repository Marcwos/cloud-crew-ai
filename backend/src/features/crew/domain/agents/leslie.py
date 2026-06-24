"""Leslie — Orchestrator agent.

Named in honor of Leslie Lamport, pioneer of distributed systems.
Leslie performs triage and consolidation. She does NOT produce a Proposal —
she produces Constraints+Tasks (triage) and FinalPlan (consolidation).
"""
from __future__ import annotations

from src.features.crew.domain.entities.final_plan import FinalPlan
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.ports.llm_provider import LLMProvider, LLMRequest, LLMMessage
from src.features.crew.domain.ports.knowledge_source import KnowledgeSource
from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.domain.agents._parsers import (
    parse_multiline_section,
    parse_single_line_section,
    parse_list_section,
    parse_kv_section,
)

_VALID_CONSTRAINT_KINDS = {"cost", "security", "latency", "scale", "compliance"}

_SPECIALIST_AGENTS = ("alan", "edgar", "hedy", "grace", "vint")

_TRIAGE_SYSTEM = (
    "You are Leslie, the orchestrator agent named in honor of Leslie Lamport. "
    "You receive a user challenge and perform triage: identify key constraints and assign tasks "
    "to each specialist (alan=compute, edgar=data, hedy=security, grace=monitoring/cost, vint=networking). "
    "Respond in this exact format:\n"
    "CONSTRAINTS:\n- <kind>: <detail>\n...\n"
    "TASKS:\n- <agent>: <task description>\n...\n"
    "Valid constraint kinds: cost, security, latency, scale, compliance."
)

_CONSOLIDATE_SYSTEM = (
    "You are Leslie, the orchestrator. You receive proposals and reviews from specialists "
    "and produce a coherent final architecture plan. "
    "Respond in this exact format:\n"
    "SUMMARY: <one paragraph summary>\n"
    "SERVICES: <comma-separated list of all recommended services>\n"
    "JUSTIFICATION:\n- <service>: <justification>\n...\n"
    "DIAGRAM_HINT: <short textual description of the architecture flow>"
)


class LeslieAgent:
    """Orchestrator: triage + consolidation. Does not produce Proposals."""

    def __init__(self, llm: LLMProvider, knowledge: KnowledgeSource) -> None:
        self._llm = llm
        self._knowledge = knowledge

    async def triage(self, challenge: str) -> tuple[list[Constraint], dict[str, str]]:
        """Extract constraints and assign tasks from a challenge description."""
        request = LLMRequest(
            model="claude-3-5-sonnet-20241022",
            system=_TRIAGE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        f"Challenge: {challenge}\n\n"
                        "Identify the key constraints and assign one task per specialist."
                    ),
                )
            ],
        )
        response = await self._llm.complete(request)
        return self._parse_triage(response.text)

    async def consolidate(
        self,
        proposals: list[Proposal],
        reviews: list[Review],
    ) -> FinalPlan:
        """Consolidate proposals and reviews into an integrated FinalPlan."""
        proposals_text = "\n\n".join(
            f"[{p.agent.upper()}]\nServices: {', '.join(p.services)}\n"
            f"Rationale: {p.rationale}\n"
            f"Rejected: {', '.join(p.alternatives_rejected)}\n"
            f"Trade-offs: {p.trade_offs}"
            for p in proposals
        )
        reviews_text = "\n\n".join(
            f"[REVIEW by {r.reviewer} → {r.target_agent}]\n"
            f"Challenge: {r.challenge}\nTrade-off: {r.trade_off}"
            for r in reviews
        ) or "No reviews submitted."

        request = LLMRequest(
            model="claude-3-5-sonnet-20241022",
            system=_CONSOLIDATE_SYSTEM,
            messages=[
                LLMMessage(
                    role="user",
                    content=(
                        f"Specialist proposals:\n{proposals_text}\n\n"
                        f"Cross-reviews:\n{reviews_text}\n\n"
                        "Produce the integrated final plan."
                    ),
                )
            ],
        )
        response = await self._llm.complete(request)
        return self._parse_final_plan(response.text)

    # ------------------------------------------------------------------
    # Private parsing helpers
    # ------------------------------------------------------------------

    def _parse_triage(self, text: str) -> tuple[list[Constraint], dict[str, str]]:
        raw_constraints = parse_multiline_section(text, "CONSTRAINTS")
        constraints: list[Constraint] = []
        for item in raw_constraints:
            if ":" in item:
                kind_raw, _, detail = item.partition(":")
                kind = kind_raw.strip().lower()
                detail = detail.strip()
                if kind in _VALID_CONSTRAINT_KINDS and detail:
                    constraints.append(Constraint(kind=kind, detail=detail))  # type: ignore[arg-type]

        if not constraints:
            constraints = [Constraint(kind="cost", detail="Optimize for cost efficiency")]

        raw_tasks = parse_multiline_section(text, "TASKS")
        tasks: dict[str, str] = {}
        for item in raw_tasks:
            if ":" in item:
                agent_raw, _, task_desc = item.partition(":")
                agent = agent_raw.strip().lower()
                task = task_desc.strip()
                if agent in _SPECIALIST_AGENTS and task:
                    tasks[agent] = task

        # Ensure all specialists have a task
        for agent in _SPECIALIST_AGENTS:
            if agent not in tasks:
                tasks[agent] = f"Provide {agent} architectural recommendations"

        return constraints, tasks

    def _parse_final_plan(self, text: str) -> FinalPlan:
        summary = parse_single_line_section(text, "SUMMARY")
        if not summary:
            summary = "Integrated multi-layer AWS architecture based on specialist proposals"

        raw_services = parse_list_section(text, "SERVICES")
        services = [s for s in raw_services if s]
        if not services:
            services = ["AWS Lambda"]

        justification = parse_kv_section(text, "JUSTIFICATION")

        # Ensure every service has a justification entry
        for service in services:
            if service not in justification:
                justification[service] = f"Recommended by specialist agents for this workload"

        diagram_hint = parse_single_line_section(text, "DIAGRAM_HINT")
        if not diagram_hint:
            diagram_hint = "Multi-layer AWS architecture with compute, data, security, and networking layers"

        return FinalPlan(
            summary=summary,
            services=services,
            justification_by_service=justification,
            diagram_hint=diagram_hint,
        )
