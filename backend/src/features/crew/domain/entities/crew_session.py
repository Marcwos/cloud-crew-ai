"""CrewSession entity — the shared state for a full crew workflow run."""
from __future__ import annotations

from pydantic import BaseModel, field_validator

from src.features.crew.domain.value_objects.constraint import Constraint
from src.features.crew.domain.value_objects.agent_event import AgentEvent
from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.entities.final_plan import FinalPlan


class CrewSession(BaseModel):
    """The complete state of a crew session: triage, proposals, reviews, and final plan."""

    session_id: str
    challenge: str
    constraints: list[Constraint]
    tasks: dict[str, str]
    proposals: list[Proposal]
    reviews: list[Review]
    final_plan: FinalPlan | None
    events: list[AgentEvent]

    @field_validator("session_id")
    @classmethod
    def session_id_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id must not be blank")
        return v

    @field_validator("challenge")
    @classmethod
    def challenge_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("challenge must not be blank")
        return v
