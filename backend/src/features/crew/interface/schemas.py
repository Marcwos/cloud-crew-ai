"""Pydantic schemas for HTTP request/response DTOs."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Bound the challenge length to protect downstream LLM prompts and the queue
# from oversized input. 4000 chars is generous for an architecture brief.
CHALLENGE_MAX_LENGTH = 4000


class StartSessionRequest(BaseModel):
    """Body for POST /api/sessions."""

    challenge: str = Field(min_length=1, max_length=CHALLENGE_MAX_LENGTH)

    @field_validator("challenge")
    @classmethod
    def challenge_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("challenge must not be blank")
        return v


class StartSessionResponse(BaseModel):
    """Response body for POST /api/sessions (201)."""

    session_id: str


class HealthResponse(BaseModel):
    """Response body for GET /api/health."""

    status: str = "ok"
