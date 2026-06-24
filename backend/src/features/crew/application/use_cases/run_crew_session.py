"""run_crew_session use case — orchestrates the full crew workflow.

Sequence:
1. Leslie triage → constraints + tasks
2. Specialists propose (sequential here; LangGraph fan-out comes in next agent)
3. Grace reviews Alan's proposal (1-round cross-review)
4. Leslie consolidates → FinalPlan
5. Events are published at each stage
6. Session is persisted
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.features.crew.domain.agents.leslie import LeslieAgent
from src.features.crew.domain.agents.alan import AlanAgent
from src.features.crew.domain.agents.edgar import EdgarAgent
from src.features.crew.domain.agents.hedy import HedyAgent
from src.features.crew.domain.agents.grace import GraceAgent
from src.features.crew.domain.agents.vint import VintAgent
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.ports.llm_provider import LLMProvider
from src.features.crew.domain.ports.knowledge_source import KnowledgeSource
from src.features.crew.domain.ports.crew_repository import CrewRepository
from src.features.crew.domain.ports.event_publisher import EventPublisher
from src.features.crew.domain.value_objects.agent_event import AgentEvent


@dataclass
class CrewSessionDeps:
    """All port dependencies for run_crew_session — injected at composition root."""

    llm: LLMProvider
    knowledge: KnowledgeSource
    repo: CrewRepository
    events: EventPublisher


async def _emit(
    events: EventPublisher,
    session_id: str,
    agent: str,
    action: str,
    message: str,
) -> AgentEvent:
    """Helper: create, record, and publish an AgentEvent."""
    event = AgentEvent(agent=agent, action=action, status="ok", message=message)  # type: ignore[arg-type]
    await events.publish(session_id, event)
    return event


async def run_crew_session(challenge: str, deps: CrewSessionDeps) -> CrewSession:
    """Run a full crew session for the given challenge.

    Returns a fully-populated CrewSession with proposals, reviews, final_plan, and events.
    """
    session_id = str(uuid.uuid4())
    emitted_events: list[AgentEvent] = []

    # ------------------------------------------------------------------
    # Phase 1: Leslie triage
    # ------------------------------------------------------------------
    leslie = LeslieAgent(llm=deps.llm, knowledge=deps.knowledge)

    event = await _emit(deps.events, session_id, "leslie", "analyzing", "Triaging challenge and assigning tasks")
    emitted_events.append(event)

    constraints, tasks = await leslie.triage(challenge)

    event = await _emit(deps.events, session_id, "leslie", "proposing", "Tasks distributed to specialists")
    emitted_events.append(event)

    # Build initial session state
    session = CrewSession(
        session_id=session_id,
        challenge=challenge,
        constraints=constraints,
        tasks=tasks,
        proposals=[],
        reviews=[],
        final_plan=None,
        events=list(emitted_events),
    )

    # ------------------------------------------------------------------
    # Phase 2: Specialist proposals (sequential — LangGraph fan-out later)
    # ------------------------------------------------------------------
    specialists: list[tuple[str, object]] = [
        ("alan", AlanAgent(llm=deps.llm, knowledge=deps.knowledge)),
        ("edgar", EdgarAgent(llm=deps.llm, knowledge=deps.knowledge)),
        ("hedy", HedyAgent(llm=deps.llm, knowledge=deps.knowledge)),
        ("grace", GraceAgent(llm=deps.llm, knowledge=deps.knowledge)),
        ("vint", VintAgent(llm=deps.llm, knowledge=deps.knowledge)),
    ]

    for agent_name, agent in specialists:
        event = await _emit(deps.events, session_id, agent_name, "moving", f"Moving to workstation")
        emitted_events.append(event)

        event = await _emit(deps.events, session_id, agent_name, "analyzing", f"Analyzing {agent_name} domain")
        emitted_events.append(event)

        proposal = await agent.propose(session)  # type: ignore[attr-defined]

        event = await _emit(
            deps.events, session_id, agent_name, "proposing",
            f"Proposal ready: {', '.join(proposal.services[:2])}..."
        )
        emitted_events.append(event)

        session.proposals.append(proposal)

    # ------------------------------------------------------------------
    # Phase 3: 1-round cross review (Grace reviews Alan's compute proposal)
    # ------------------------------------------------------------------
    alan_proposal = next((p for p in session.proposals if p.agent == "alan"), None)
    if alan_proposal:
        event = await _emit(
            deps.events, session_id, "grace", "reviewing",
            "Reviewing Alan's compute proposal for cost implications"
        )
        emitted_events.append(event)

        review = Review(
            reviewer="grace",
            target_agent="alan",
            challenge=(
                f"For sustained workloads, consider cost comparison between "
                f"{alan_proposal.services[0] if alan_proposal.services else 'Lambda'} "
                f"and alternatives. Cold-start mitigations increase total cost."
            ),
            trade_off="Lambda flexibility and zero idle cost vs predictable pricing of container alternatives",
        )
        session.reviews.append(review)

        event = await _emit(
            deps.events, session_id, "alan", "reviewing",
            "Acknowledged Grace's cost review — trade-offs noted in final plan"
        )
        emitted_events.append(event)

    # ------------------------------------------------------------------
    # Phase 4: Leslie consolidates
    # ------------------------------------------------------------------
    event = await _emit(
        deps.events, session_id, "leslie", "analyzing",
        "Consolidating all proposals and reviews into final plan"
    )
    emitted_events.append(event)

    final_plan = await leslie.consolidate(session.proposals, session.reviews)

    event = await _emit(deps.events, session_id, "leslie", "done", "Final architecture plan ready")
    emitted_events.append(event)

    # Mark all specialists as done
    for agent_name, _ in specialists:
        event = await _emit(deps.events, session_id, agent_name, "done", "Session complete")
        emitted_events.append(event)

    # ------------------------------------------------------------------
    # Finalize session
    # ------------------------------------------------------------------
    final_session = CrewSession(
        session_id=session_id,
        challenge=challenge,
        constraints=constraints,
        tasks=tasks,
        proposals=session.proposals,
        reviews=session.reviews,
        final_plan=final_plan,
        events=emitted_events,
    )

    await deps.repo.save(final_session)
    return final_session
