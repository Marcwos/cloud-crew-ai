"""Pydantic schemas for HTTP request/response DTOs."""
from __future__ import annotations

from pydantic import BaseModel, field_validator


class StartSessionRequest(BaseModel):
    """Body for POST /api/sessions."""

    challenge: str

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
