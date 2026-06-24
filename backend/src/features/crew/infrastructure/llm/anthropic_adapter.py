"""AnthropicAdapter — LLMProvider implementation using the Anthropic SDK.

Reads ANTHROPIC_API_KEY from env if no api_key is passed explicitly.
All SDK calls are async. Tests mock `anthropic` at import level.
"""
from __future__ import annotations

import os

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse


class AnthropicAdapter:
    """LLMProvider adapter for the Anthropic Messages API (Claude models)."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if anthropic is None:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Call Anthropic's messages.create and return an LLMResponse."""
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
            if msg.role != "system"  # Anthropic handles system separately
        ]

        response = await self._client.messages.create(
            model=request.model,
            system=request.system,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        text = response.content[0].text if response.content else ""
        return LLMResponse(text=text, model=response.model)
