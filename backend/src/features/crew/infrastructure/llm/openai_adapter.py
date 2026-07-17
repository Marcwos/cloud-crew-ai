"""OpenAIAdapter — LLMProvider implementation using the OpenAI SDK.

Reads OPENAI_API_KEY from env if no api_key is passed explicitly.
Tests mock `openai` at import level.
"""
from __future__ import annotations

import os

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse


class OpenAIAdapter:
    """LLMProvider adapter for the OpenAI Chat Completions API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if openai is None:
            raise ImportError("openai package is required. Install with: pip install openai")
        kwargs: dict = {"api_key": resolved_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.AsyncOpenAI(**kwargs)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Call OpenAI's chat.completions.create and return an LLMResponse."""
        messages = [{"role": "system", "content": request.system}]
        messages.extend(
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        )

        # Newer OpenAI models (gpt-5.x, o-series) reject two things older models
        # accepted:
        #   - `max_tokens` -> they require `max_completion_tokens`.
        #   - a custom `temperature` -> they only allow the default (1).
        # So we send the new token param and omit temperature entirely, letting
        # each model use its own default. This works across old and new models,
        # and the crew never relies on a specific temperature anyway. DeepSeek
        # keeps the older shape in its own adapter.
        completion = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_completion_tokens=request.max_tokens,
        )

        text = completion.choices[0].message.content or ""
        return LLMResponse(text=text, model=completion.model)
