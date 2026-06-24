"""LLM provider factory — selects the right adapter based on config.

Usage:
    provider = make_llm_provider(provider_name, config)

The provider_name is typically read from the LLM_PROVIDER env var.
Config is a dict of adapter-specific kwargs (e.g. api_key).
"""
from __future__ import annotations

from src.features.crew.domain.ports.llm_provider import LLMProvider


def make_llm_provider(provider_name: str, config: dict) -> LLMProvider:
    """Return the appropriate LLMProvider adapter for the given provider name.

    Falls back to FakeLLMProvider for unknown or 'fake' providers.
    """
    name = (provider_name or "fake").lower()

    if name == "anthropic":
        from src.features.crew.infrastructure.llm.anthropic_adapter import AnthropicAdapter
        return AnthropicAdapter(api_key=config.get("api_key"))

    if name == "openai":
        from src.features.crew.infrastructure.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=config.get("api_key"))

    if name == "deepseek":
        from src.features.crew.infrastructure.llm.deepseek_adapter import DeepSeekAdapter
        return DeepSeekAdapter(api_key=config.get("api_key"))

    if name == "bedrock":
        from src.features.crew.infrastructure.llm.bedrock_adapter import BedrockAdapter
        return BedrockAdapter(region_name=config.get("region_name"))

    # Default: fake provider (for tests and local dev without real credentials)
    from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
    return FakeLLMProvider()
