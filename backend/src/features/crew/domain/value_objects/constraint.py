"""Constraint value object — pure domain, no framework imports."""
from typing import Literal

from pydantic import BaseModel, field_validator


class Constraint(BaseModel, frozen=True):
    """Represents a requirement constraint extracted from the user challenge."""

    kind: Literal["cost", "security", "latency", "scale", "compliance"]
    detail: str

    @field_validator("detail")
    @classmethod
    def detail_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("detail must not be blank")
        return v
