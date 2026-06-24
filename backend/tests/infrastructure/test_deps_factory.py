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
                deps = factory_mod.build_deps()
                assert isinstance(deps.llm, OpenAIAdapter)

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
