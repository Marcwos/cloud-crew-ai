"""LangGraph-based orchestration for the Cloud Crew AI workflow.

Graph shape:
  leslie_triage
       |
  [fan-out: alan, edgar, hedy, grace, vint run in parallel]
       |
  fan_in
       |
  review_round ──(contested_service)──> re_propose ──┐
       └──────────────(no conflict)────────────────> leslie_consolidate

`review_round` generates a real cross-review via `CrossReviewer` (WU3) and
checks it for a strong conflict via `has_strong_conflict`/`find_contested_service`
(WU2, pure domain rule — LLM produces the ARGUMENT, the domain decides the
CONFLICT). When there is one, `re_propose` (WU4) revises the target's
proposal once; `re_propose` always edges to `leslie_consolidate` and NEVER
back to `review_round` — the one-round bound is topological (acyclic graph),
not a counter (design D5).

Events are published through the EventPublisher port at each transition.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Literal, TypedDict

from langgraph.graph import StateGraph, END

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent
from src.features.crew.domain.agents.alan import AlanAgent
from src.features.crew.domain.agents.edgar import EdgarAgent
from src.features.crew.domain.agents.grace import GraceAgent
from src.features.crew.domain.agents.hedy import HedyAgent
from src.features.crew.domain.agents.leslie import LeslieAgent
from src.features.crew.domain.agents.reviewer import CrossReviewer
from src.features.crew.domain.agents.vint import VintAgent
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.domain.entities.final_plan import FinalPlan
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.policies.debate import find_contested_service
from src.features.crew.domain.value_objects.agent_event import AgentEvent
from src.features.crew.domain.value_objects.constraint import Constraint

# Promotes the fan-out's local agent list (previously inline in
# `_make_parallel_specialists_node`) to a module-level registry shared by
# fan-out, `review_round`, and `re_propose` (design §6.3).
_SPECIALIST_REGISTRY: dict[str, type[BaseSpecialistAgent]] = {
    "alan": AlanAgent,
    "edgar": EdgarAgent,
    "hedy": HedyAgent,
    "grace": GraceAgent,
    "vint": VintAgent,
}


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
    # Canonical name of the catalog service the reviewer contests and the
    # target already rejected — `None` when there is no strong conflict.
    # The single new field this change adds to state (design §6.1/A7): it
    # doubles as the routing signal (truthy => conflict) and the input to
    # the re-propose prompt. No `review_rounds` counter — the bound is
    # topological (D5).
    contested_service: str | None


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


def _session_view(state: GraphState) -> CrewSession:
    """Build a read-only `CrewSession` snapshot from graph state — the shape
    `CrossReviewer.review()` and `BaseSpecialistAgent.re_propose()` expect.
    Never persisted; `events` is left empty since neither call needs it.
    """
    return CrewSession(
        session_id=state["session_id"],
        challenge=state["challenge"],
        constraints=state.get("constraints", []),
        tasks=state.get("tasks", {}),
        proposals=state.get("proposals", []),
        reviews=state.get("reviews", []),
        final_plan=None,
        events=[],
    )


def _make_review_node(deps: CrewSessionDeps):
    async def review_round(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        events: list[AgentEvent] = list(state.get("events", []))
        proposals: list[Proposal] = state.get("proposals", [])
        reviews: list[Review] = list(state.get("reviews", []))

        # LLM generates the ARGUMENT. `_parse_review` already discards
        # malformed output (unknown agent, reviewer == target, target with
        # no proposal in state, blank challenge) — R8, no fabrication.
        reviewer = CrossReviewer(llm=deps.llm)
        review = await reviewer.review(_session_view(state), proposals)

        if review is None:
            return {**state, "contested_service": None}

        event = await _emit(
            deps, session_id, review.reviewer, "reviewing",
            f"Challenging {review.target_agent}'s proposal: {review.challenge}"
        )
        events.append(event)

        target_proposal = next((p for p in proposals if p.agent == review.target_agent), None)
        if target_proposal is None:
            # Defensive — `_parse_review` already guarantees the target has a
            # proposal, but never trust an LLM-shaped invariant twice.
            return {**state, "events": events, "contested_service": None}

        # Domain DECIDES the conflict — scoped to the target's own domain
        # catalog (design §2.3): a contested service outside it could never
        # be re-proposed anyway, so scoping it here makes conflict imply an
        # actionable re-proposal by construction.
        target_agent_cls = _SPECIALIST_REGISTRY[review.target_agent]
        target_agent = target_agent_cls(llm=deps.llm, knowledge=deps.knowledge)
        facts = await deps.knowledge.services_for(target_agent.domain, state["challenge"])
        catalog_names = frozenset(f.name for f in facts)
        contested = find_contested_service(review, target_proposal, catalog_names)

        return {
            **state,
            "reviews": reviews + [review],
            "events": events,
            "contested_service": contested,
        }

    return review_round


def _route_after_review(state: GraphState) -> Literal["re_propose", "leslie_consolidate"]:
    """Pure router — no I/O. Truthy `contested_service` means a strong
    conflict was found; route to `re_propose`. Otherwise go straight to
    consolidation. This is the graph's only branch point (design §6.3).
    """
    return "re_propose" if state.get("contested_service") else "leslie_consolidate"


def _make_re_propose_node(deps: CrewSessionDeps):
    async def re_propose(state: GraphState) -> GraphState:
        session_id = state["session_id"]
        events: list[AgentEvent] = list(state.get("events", []))
        reviews: list[Review] = state.get("reviews", [])
        proposals: list[Proposal] = state.get("proposals", [])
        contested = state.get("contested_service")

        review = reviews[-1]
        target = review.target_agent

        event = await _emit(
            deps, session_id, target, "analyzing",
            f"Reconsidering {contested} after {review.reviewer}'s challenge"
        )
        events.append(event)

        target_agent_cls = _SPECIALIST_REGISTRY[target]
        agent = target_agent_cls(llm=deps.llm, knowledge=deps.knowledge)
        original = next(p for p in proposals if p.agent == target)

        revised = await agent.re_propose(_session_view(state), original, review, contested)

        if revised is None:
            # Ungrounded/unparseable revision — keep the ORIGINAL proposal.
            # The graph never degrades the plan (design §4).
            return {**state, "events": events}

        event = await _emit(
            deps, session_id, target, "proposing",
            f"Revised proposal after debate on {contested}: {', '.join(revised.services[:2])}"
        )
        events.append(event)

        # REPLACE by index, never append — a second "alan" entry would break
        # the "one proposal per specialist" contract (design §0.2/D6).
        updated_proposals = [revised if p.agent == target else p for p in proposals]

        return {**state, "proposals": updated_proposals, "events": events}

    return re_propose


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

        # Fan-out: run all 5 concurrently (still asyncio.gather, not Send —
        # the fan-out happens inside a single node, so LangGraph never sees
        # concurrent writes; design §6.2 explains why no reducer is needed).
        results = await asyncio.gather(
            *[run_specialist(name, cls) for name, cls in _SPECIALIST_REGISTRY.items()]
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
    graph.add_node("re_propose", _make_re_propose_node(deps))
    graph.add_node("leslie_consolidate", _make_consolidate_node(deps))

    graph.set_entry_point("leslie_triage")
    graph.add_edge("leslie_triage", "specialists")
    graph.add_edge("specialists", "review_round")
    # Conditional branch: strong conflict -> re_propose, else straight to
    # consolidate. `re_propose` always edges to `leslie_consolidate` and
    # NEVER back to `review_round` — the graph is acyclic, so the one-round
    # bound holds by construction (design D5), not by a counter.
    graph.add_conditional_edges(
        "review_round", _route_after_review, ["re_propose", "leslie_consolidate"]
    )
    graph.add_edge("re_propose", "leslie_consolidate")
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
        "contested_service": None,
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
