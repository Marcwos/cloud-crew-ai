"""Proposal entity — a specialist agent's recommendation, with required justification."""
from pydantic import BaseModel, field_validator


class Proposal(BaseModel):
    """An agent's architectural proposal. INVALID without rationale AND alternatives_rejected."""

    agent: str
    services: list[str]
    rationale: str
    alternatives_rejected: list[str]
    trade_offs: str

    @field_validator("rationale")
    @classmethod
    def rationale_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("rationale must not be blank — a proposal without justification is invalid")
        return v

    @field_validator("alternatives_rejected")
    @classmethod
    def alternatives_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError(
                "alternatives_rejected must not be empty — "
                "a proposal must explain what was considered and rejected"
            )
        return v

    @field_validator("services")
    @classmethod
    def services_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("services must not be empty")
        return v
