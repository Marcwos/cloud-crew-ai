"""AgentEvent value object — represents a moment in an agent's lifecycle for SSE."""
from typing import Literal

from pydantic import BaseModel, field_validator


class AgentEvent(BaseModel, frozen=True):
    """An immutable event emitted by an agent, streamed to the frontend via SSE."""

    agent: str
    action: Literal["idle", "moving", "analyzing", "proposing", "reviewing", "done"]
    status: str
    message: str
    # The concrete brief Leslie assigned to this specialist. Optional so
    # lifecycle events that do not represent an assignment remain compatible.
    assignment: str | None = None

    @field_validator("agent")
    @classmethod
    def agent_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("agent must not be blank")
        return v
