"""LLMProvider port — Protocol defining the LLM interface for agent use."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LLMMessage(BaseModel, frozen=True):
    """A single message in a conversation with an LLM."""

    role: str  # "user" | "assistant" | "system"
    content: str


class LLMRequest(BaseModel, frozen=True):
    """Request parameters for an LLM completion call."""

    model: str
    system: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int = 2048


class LLMResponse(BaseModel, frozen=True):
    """Response from an LLM completion call."""

    text: str
    model: str


@runtime_checkable
class LLMProvider(Protocol):
    """Port: abstracting the LLM provider. Agents depend on this, not any SDK."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complete a prompt and return the model's response."""
        ...
