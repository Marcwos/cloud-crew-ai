"""DeepSeekAdapter — LLMProvider using DeepSeek's OpenAI-compatible API.

DeepSeek exposes an OpenAI-compatible endpoint, so we reuse the openai SDK
with a custom base_url. Reads DEEPSEEK_API_KEY from env if not passed.
Tests mock `openai` at import level.
"""
from __future__ import annotations

import os

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekAdapter:
    """LLMProvider adapter for the DeepSeek API (OpenAI-compatible shape)."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if openai is None:
            raise ImportError("openai package is required. Install with: pip install openai")
        self._client = openai.AsyncOpenAI(
            api_key=resolved_key,
            base_url=_DEEPSEEK_BASE_URL,
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Call DeepSeek's chat completions endpoint."""
        messages = [{"role": "system", "content": request.system}]
        messages.extend(
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        )

        completion = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        text = completion.choices[0].message.content or ""
        return LLMResponse(text=text, model=completion.model)
