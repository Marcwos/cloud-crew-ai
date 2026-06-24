"""Review entity — a reviewer agent's challenge to another agent's proposal."""
from pydantic import BaseModel, field_validator


class Review(BaseModel):
    """A cross-review from one specialist challenging another's proposal."""

    reviewer: str
    target_agent: str
    challenge: str
    trade_off: str

    @field_validator("reviewer", "target_agent")
    @classmethod
    def agent_name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("agent name must not be blank")
        return v

    @field_validator("challenge")
    @classmethod
    def challenge_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("challenge must not be blank")
        return v
