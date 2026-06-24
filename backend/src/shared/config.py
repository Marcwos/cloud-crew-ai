"""Configuration module — reads env vars with safe defaults for local/test runs."""
import os


def get_llm_provider_name() -> str:
    """Which LLM provider adapter to use. Defaults to 'fake' for tests."""
    return os.getenv("LLM_PROVIDER", "fake")


def get_llm_model() -> str:
    """Default model identifier. Overridden per-agent in production."""
    return os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")


def get_specialist_model() -> str:
    """Model id for specialist agents (cheaper/faster tier).

    Falls back to the generic LLM_MODEL, then to the provider-neutral default.
    Reading this from config (never hardcoding a Claude id) keeps non-Anthropic
    providers — OpenAI, DeepSeek, Bedrock — working.
    """
    return os.getenv("LLM_SPECIALIST_MODEL") or get_llm_model()


def get_orchestrator_model() -> str:
    """Model id for the orchestrator (Leslie) — may be a stronger tier.

    Falls back to LLM_MODEL so a single LLM_MODEL still configures the whole crew.
    """
    return os.getenv("LLM_ORCHESTRATOR_MODEL") or get_llm_model()


def is_fake_mode() -> bool:
    """True when running with fake/test adapters (no real LLM calls)."""
    return get_llm_provider_name() == "fake"
