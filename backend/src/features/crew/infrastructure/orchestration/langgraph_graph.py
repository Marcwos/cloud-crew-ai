"""LangGraph-based orchestration for the Cloud Crew AI workflow.

Graph shape:
  leslie_triage
       |
  [fan-out: alan, edgar, hedy, grace, vint run in parallel]
       |
  fan_in
       |
  review_round
       |
  leslie_consolidate

Events are published through the EventPublisher port at each transition.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import TypedDict

from langgraph.graph import StateGraph, END

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.domain.agents.alan import AlanAgent
from src.features.crew.domain.agents.edgar import EdgarAgent
from src.features.crew.domain.agents.grace import GraceAgent
from src.features.crew.domain.agents.hedy import HedyAgent
from src.features.crew.domain.agents.leslie import LeslieAgent
from src.features.crew.domain.agents.vint import VintAgent
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.final_plan import FinalPlan
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.value_objects.agent_event import AgentEvent
from src.features.crew.domain.value_objects.constraint import Constraint


# ---------------------------------------------------------------------------
# Graph state — mutable dict passed between nodes
# ---------------------------------------------------------------------------

class GraphState(TypedDict, total=False):
    session_id: str
    challenge: str
    constraints: list[Constraint]
    tasks: dict[str, str]
    proposals: list[Proposal]
    reviews: list[Review]
    events: list[AgentEvent]
    final_plan: FinalPlan | None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _emit(
    deps: CrewSessionDeps,
    session_id: str,
    agent: str,
    action: str,
    message: str,
) -> AgentEvent:
    event = AgentEvent(agent=agent, action=action, status="ok", message=message)  # type: ignore[arg-type]
    await deps.events.publish(session_id, event)
    return event


# ---------------------------------------------------------------------------
# Node builders (closures over deps)
# ---------------------------------------------------------------------------

def _make_triage_node(deps: CrewSessionDeps):
    async def leslie_triage(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        challenge = state["challenge"]
        events: list[AgentEvent] = list(state.get("events", []))

        event = await _emit(deps, session_id, "leslie", "analyzing", "Triaging challenge and assigning tasks")
        events.append(event)

        leslie = LeslieAgent(llm=deps.llm, knowledge=deps.knowledge)
        constraints, tasks = await leslie.triage(challenge)

        event = await _emit(deps, session_id, "leslie", "proposing", "Tasks distributed to specialists")
        events.append(event)

        return {
            **state,
            "constraints": constraints,
            "tasks": tasks,
            "proposals": [],
            "reviews": [],
            "events": events,
        }

    return leslie_triage


def _make_specialist_node(agent_name: str, deps: CrewSessionDeps):
    """Build a node function for a single specialist agent."""
    _agent_classes = {
        "alan": AlanAgent,
        "edgar": EdgarAgent,
        "hedy": HedyAgent,
        "grace": GraceAgent,
        "vint": VintAgent,
    }

    async def specialist_node(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        challenge = state["challenge"]
        events: list[AgentEvent] = list(state.get("events", []))
        proposals: list[Proposal] = list(state.get("proposals", []))

        event = await _emit(deps, session_id, agent_name, "moving", "Moving to workstation")
        events.append(event)

        event = await _emit(deps, session_id, agent_name, "analyzing", f"Analyzing {agent_name} domain")
        events.append(event)

        # Build a minimal session for the agent to propose against
        temp_session = CrewSession(
            session_id=session_id,
            challenge=challenge,
            constraints=state.get("constraints", []),
            tasks=state.get("tasks", {}),
            proposals=[],
            reviews=[],
            final_plan=None,
            events=[],
        )

        agent_cls = _agent_classes[agent_name]
        agent = agent_cls(llm=deps.llm, knowledge=deps.knowledge)
        proposal = await agent.propose(temp_session)

        event = await _emit(
            deps, session_id, agent_name, "proposing",
            f"Proposal ready: {', '.join(proposal.services[:2])}..."
        )
        events.append(event)

        return {
            **state,
            "proposals": proposals + [proposal],
            "events": events,
        }

    return specialist_node


def _make_review_node(deps: CrewSessionDeps):
    async def review_round(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        events: list[AgentEvent] = list(state.get("events", []))
        proposals: list[Proposal] = state.get("proposals", [])
        reviews: list[Review] = list(state.get("reviews", []))

        alan_proposal = next((p for p in proposals if p.agent == "alan"), None)
        if alan_proposal:
            event = await _emit(
                deps, session_id, "grace", "reviewing",
                "Reviewing Alan's compute proposal for cost implications"
            )
            events.append(event)

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
            reviews.append(review)

            event = await _emit(
                deps, session_id, "alan", "reviewing",
                "Acknowledged Grace's cost review — trade-offs noted in final plan"
            )
            events.append(event)

        return {
            **state,
            "reviews": reviews,
            "events": events,
        }

    return review_round


def _make_consolidate_node(deps: CrewSessionDeps):
    async def leslie_consolidate(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        proposals: list[Proposal] = state.get("proposals", [])
        reviews: list[Review] = state.get("reviews", [])
        events: list[AgentEvent] = list(state.get("events", []))

        event = await _emit(
            deps, session_id, "leslie", "analyzing",
            "Consolidating all proposals and reviews into final plan"
        )
        events.append(event)

        leslie = LeslieAgent(llm=deps.llm, knowledge=deps.knowledge)
        final_plan = await leslie.consolidate(proposals, reviews)

        event = await _emit(deps, session_id, "leslie", "done", "Final architecture plan ready")
        events.append(event)

        # Mark all specialists as done
        for agent_name in ("alan", "edgar", "hedy", "grace", "vint"):
            event = await _emit(deps, session_id, agent_name, "done", "Session complete")
            events.append(event)

        return {
            **state,
            "final_plan": final_plan,
            "events": events,
        }

    return leslie_consolidate


# ---------------------------------------------------------------------------
# Fan-out node: runs all 5 specialists in parallel
# ---------------------------------------------------------------------------

def _make_parallel_specialists_node(deps: CrewSessionDeps):
    """Run all 5 specialist nodes concurrently, then merge their proposals."""

    async def parallel_specialists(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        challenge = state["challenge"]
        events: list[AgentEvent] = list(state.get("events", []))

        # Build a shared temp session for all agents
        temp_session = CrewSession(
            session_id=session_id,
            challenge=challenge,
            constraints=state.get("constraints", []),
            tasks=state.get("tasks", {}),
            proposals=[],
            reviews=[],
            final_plan=None,
            events=[],
        )

        specialist_configs: list[tuple[str, type]] = [
            ("alan", AlanAgent),
            ("edgar", EdgarAgent),
            ("hedy", HedyAgent),
            ("grace", GraceAgent),
            ("vint", VintAgent),
        ]

        async def run_specialist(agent_name: str, agent_cls: type) -> tuple[AgentEvent, AgentEvent, Proposal, AgentEvent]:
            e_moving = await _emit(deps, session_id, agent_name, "moving", "Moving to workstation")
            e_analyzing = await _emit(deps, session_id, agent_name, "analyzing", f"Analyzing {agent_name} domain")

            agent = agent_cls(llm=deps.llm, knowledge=deps.knowledge)
            proposal = await agent.propose(temp_session)

            e_proposing = await _emit(
                deps, session_id, agent_name, "proposing",
                f"Proposal ready: {', '.join(proposal.services[:2])}..."
            )
            return e_moving, e_analyzing, proposal, e_proposing

        # Fan-out: run all 5 concurrently
        results = await asyncio.gather(
            *[run_specialist(name, cls) for name, cls in specialist_configs]
        )

        # Collect results in deterministic order (alan, edgar, hedy, grace, vint)
        proposals: list[Proposal] = []
        for e_moving, e_analyzing, proposal, e_proposing in results:
            events.append(e_moving)
            events.append(e_analyzing)
            proposals.append(proposal)
            events.append(e_proposing)

        return {
            **state,
            "proposals": proposals,
            "events": events,
        }

    return parallel_specialists


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def _build_graph(deps: CrewSessionDeps) -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("leslie_triage", _make_triage_node(deps))
    graph.add_node("specialists", _make_parallel_specialists_node(deps))
    graph.add_node("review_round", _make_review_node(deps))
    graph.add_node("leslie_consolidate", _make_consolidate_node(deps))

    graph.set_entry_point("leslie_triage")
    graph.add_edge("leslie_triage", "specialists")
    graph.add_edge("specialists", "review_round")
    graph.add_edge("review_round", "leslie_consolidate")
    graph.add_edge("leslie_consolidate", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_graph(
    challenge: str,
    deps: CrewSessionDeps,
    session_id: str | None = None,
) -> CrewSession:
    """Execute the full crew workflow via LangGraph and return a populated CrewSession.

    This is the entry point called by the use case / route. It does NOT persist the
    session — the caller is responsible for that.

    The caller may pass session_id so that every published AgentEvent is keyed to the
    same id the client received (the SSE queue is keyed by this id). When omitted, a
    fresh id is generated.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    graph = _build_graph(deps)

    initial_state: GraphState = {
        "session_id": session_id,
        "challenge": challenge,
        "constraints": [],
        "tasks": {},
        "proposals": [],
        "reviews": [],
        "events": [],
        "final_plan": None,
    }

    final_state = await graph.ainvoke(initial_state)

    return CrewSession(
        session_id=session_id,
        challenge=challenge,
        constraints=final_state.get("constraints", []),
        tasks=final_state.get("tasks", {}),
        proposals=final_state.get("proposals", []),
        reviews=final_state.get("reviews", []),
        final_plan=final_state.get("final_plan"),
        events=final_state.get("events", []),
    )
