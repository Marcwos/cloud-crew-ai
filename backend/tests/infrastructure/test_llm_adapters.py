"""Tests for LLM provider adapters — RED first.

All tests MOCK the SDK clients — no real API calls are made.
Each adapter must implement the LLMProvider port (async complete method).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMMessage, LLMResponse
from src.features.crew.infrastructure.llm.anthropic_adapter import AnthropicAdapter
from src.features.crew.infrastructure.llm.openai_adapter import OpenAIAdapter
from src.features.crew.infrastructure.llm.deepseek_adapter import DeepSeekAdapter
from src.features.crew.infrastructure.llm.llm_factory import make_llm_provider


def _make_request(system: str = "You are a test assistant") -> LLMRequest:
    return LLMRequest(
        model="claude-3-5-haiku-20241022",
        system=system,
        messages=[LLMMessage(role="user", content="Hello")],
        temperature=0.7,
        max_tokens=256,
    )


class TestAnthropicAdapter:
    async def test_complete_returns_llm_response(self):
        with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncAnthropic.return_value = mock_client

            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="Hello from Claude")]
            mock_message.model = "claude-3-5-haiku-20241022"
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            adapter = AnthropicAdapter(api_key="test-key")
            request = _make_request()
            response = await adapter.complete(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "Hello from Claude"
            assert response.model == "claude-3-5-haiku-20241022"

    async def test_complete_passes_system_prompt(self):
        with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncAnthropic.return_value = mock_client

            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="response")]
            mock_message.model = "claude-3-5-haiku-20241022"
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            adapter = AnthropicAdapter(api_key="test-key")
            request = _make_request(system="You are Leslie")
            await adapter.complete(request)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["system"] == "You are Leslie"

    async def test_complete_passes_temperature_and_max_tokens(self):
        with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncAnthropic.return_value = mock_client

            mock_message = MagicMock()
            mock_message.content = [MagicMock(text="ok")]
            mock_message.model = "test"
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            adapter = AnthropicAdapter(api_key="test-key")
            request = LLMRequest(
                model="claude-3-5-haiku-20241022",
                system="system",
                messages=[LLMMessage(role="user", content="hi")],
                temperature=0.3,
                max_tokens=512,
            )
            await adapter.complete(request)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["temperature"] == 0.3
            assert call_kwargs["max_tokens"] == 512

    async def test_reads_api_key_from_env_when_not_provided(self):
        """Adapter should read ANTHROPIC_API_KEY from env if not passed."""
        with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic") as mock_sdk:
            import os
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
                mock_client = MagicMock()
                mock_sdk.AsyncAnthropic.return_value = mock_client

                adapter = AnthropicAdapter()  # no explicit key
                # Just check it initialises without raising
                assert adapter is not None


class TestOpenAIAdapter:
    async def test_complete_returns_llm_response(self):
        with patch("src.features.crew.infrastructure.llm.openai_adapter.openai") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncOpenAI.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from GPT"
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            mock_completion.model = "gpt-4o-mini"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            adapter = OpenAIAdapter(api_key="test-key")
            request = _make_request()
            response = await adapter.complete(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "Hello from GPT"

    async def test_complete_passes_system_as_message(self):
        with patch("src.features.crew.infrastructure.llm.openai_adapter.openai") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncOpenAI.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "ok"
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            mock_completion.model = "gpt-4o-mini"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            adapter = OpenAIAdapter(api_key="test-key")
            request = _make_request(system="You are an expert")
            await adapter.complete(request)

            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            messages = call_kwargs["messages"]
            system_messages = [m for m in messages if m["role"] == "system"]
            assert len(system_messages) == 1
            assert system_messages[0]["content"] == "You are an expert"


class TestDeepSeekAdapter:
    async def test_complete_returns_llm_response(self):
        with patch("src.features.crew.infrastructure.llm.deepseek_adapter.openai") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncOpenAI.return_value = mock_client

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello from DeepSeek"
            mock_completion = MagicMock()
            mock_completion.choices = [mock_choice]
            mock_completion.model = "deepseek-chat"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

            adapter = DeepSeekAdapter(api_key="test-key")
            request = _make_request()
            response = await adapter.complete(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "Hello from DeepSeek"

    async def test_uses_deepseek_base_url(self):
        with patch("src.features.crew.infrastructure.llm.deepseek_adapter.openai") as mock_sdk:
            mock_client = MagicMock()
            mock_sdk.AsyncOpenAI.return_value = mock_client

            DeepSeekAdapter(api_key="test-key")

            call_kwargs = mock_sdk.AsyncOpenAI.call_args.kwargs
            assert "deepseek" in call_kwargs.get("base_url", "").lower()


class TestMakeLLMProvider:
    def test_returns_fake_when_fake_config(self):
        from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
        provider = make_llm_provider("fake", {})
        assert isinstance(provider, FakeLLMProvider)

    def test_returns_anthropic_adapter_when_configured(self):
        with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic"):
            provider = make_llm_provider("anthropic", {"api_key": "test-key"})
            assert isinstance(provider, AnthropicAdapter)

    def test_returns_openai_adapter_when_configured(self):
        with patch("src.features.crew.infrastructure.llm.openai_adapter.openai"):
            provider = make_llm_provider("openai", {"api_key": "test-key"})
            assert isinstance(provider, OpenAIAdapter)

    def test_returns_deepseek_adapter_when_configured(self):
        with patch("src.features.crew.infrastructure.llm.deepseek_adapter.openai"):
            provider = make_llm_provider("deepseek", {"api_key": "test-key"})
            assert isinstance(provider, DeepSeekAdapter)

    def test_defaults_to_fake_for_unknown_provider(self):
        from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
        provider = make_llm_provider("unknown_provider", {})
        assert isinstance(provider, FakeLLMProvider)
