"""Tests for composition root factory — RED first.

Verifies that build_deps returns the right adapters based on config,
without actually calling real external services.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
import os


class TestBuildDeps:
    def test_build_deps_returns_fake_in_default_mode(self):
        """Without LLM_PROVIDER set, build_deps uses FakeLLMProvider."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "fake"}):
            from src.shared.deps_factory import build_deps
            deps = build_deps()
            from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
            assert isinstance(deps.llm, FakeLLMProvider)

    def test_build_deps_real_mode_uses_sse_publisher(self):
        """When LLM_PROVIDER != fake, build_deps wires SSEEventPublisher."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "test-key",
        }):
            with patch("src.features.crew.infrastructure.llm.anthropic_adapter.anthropic") as mock_sdk:
                mock_client = object()
                mock_sdk.AsyncAnthropic.return_value = mock_client

                # Re-import to pick up env change
                import importlib
                import src.shared.deps_factory as factory_mod
                importlib.reload(factory_mod)

                from src.features.crew.infrastructure.events.sse_event_publisher import SSEEventPublisher
                deps = factory_mod.build_deps()
                assert isinstance(deps.events, SSEEventPublisher)

    def test_build_deps_real_mode_uses_configured_llm(self):
        """When LLM_PROVIDER=openai, build_deps uses OpenAIAdapter."""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("src.features.crew.infrastructure.llm.openai_adapter.openai"):
                import importlib
                import src.shared.deps_factory as factory_mod
                import src.shared.config as config_mod
                importlib.reload(config_mod)
                importlib.reload(factory_mod)

                from src.features.crew.infrastructure.llm.openai_adapter import OpenAIAdapter
                from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider
                deps = factory_mod.build_deps()
                # Real providers are wrapped for timeout + retry; the configured
                # adapter is the inner provider.
                assert isinstance(deps.llm, ResilientLLMProvider)
                assert isinstance(deps.llm._inner, OpenAIAdapter)

    def test_build_deps_fake_when_no_provider_set(self):
        """Completely absent LLM_PROVIDER env var defaults to fake."""
        env = {k: v for k, v in os.environ.items() if k != "LLM_PROVIDER"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import src.shared.config as config_mod
            import src.shared.deps_factory as factory_mod
            importlib.reload(config_mod)
            importlib.reload(factory_mod)

            deps = factory_mod.build_deps()
            from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
            assert isinstance(deps.llm, FakeLLMProvider)


class TestApiKeyForProvider:
    """The api key must be selected by provider, never a first-non-empty scan.

    Regression guard: a first-non-empty scan passed an ANTHROPIC_API_KEY to the
    OpenAI adapter whenever both keys were set, breaking auth silently.
    """

    def test_openai_provider_uses_openai_key_even_when_anthropic_key_present(self):
        from src.shared.deps_factory import _api_key_for_provider

        environ = {"ANTHROPIC_API_KEY": "anthropic-secret", "OPENAI_API_KEY": "openai-secret"}
        assert _api_key_for_provider("openai", environ) == "openai-secret"

    def test_anthropic_provider_uses_anthropic_key(self):
        from src.shared.deps_factory import _api_key_for_provider

        environ = {"ANTHROPIC_API_KEY": "anthropic-secret", "OPENAI_API_KEY": "openai-secret"}
        assert _api_key_for_provider("anthropic", environ) == "anthropic-secret"

    def test_deepseek_provider_uses_deepseek_key(self):
        from src.shared.deps_factory import _api_key_for_provider

        environ = {"OPENAI_API_KEY": "openai-secret", "DEEPSEEK_API_KEY": "deepseek-secret"}
        assert _api_key_for_provider("deepseek", environ) == "deepseek-secret"

    def test_bedrock_provider_has_no_api_key(self):
        from src.shared.deps_factory import _api_key_for_provider

        assert _api_key_for_provider("bedrock", {"AWS_DEFAULT_REGION": "us-east-1"}) is None

    def test_missing_key_returns_none(self):
        from src.shared.deps_factory import _api_key_for_provider

        assert _api_key_for_provider("openai", {}) is None

    def test_provider_name_is_case_insensitive(self):
        from src.shared.deps_factory import _api_key_for_provider

        assert _api_key_for_provider("OpenAI", {"OPENAI_API_KEY": "k"}) == "k"
