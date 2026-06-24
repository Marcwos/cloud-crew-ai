"""Configuration module — reads env vars with safe defaults for local/test runs."""
import os


def get_llm_provider_name() -> str:
    """Which LLM provider adapter to use. Defaults to 'fake' for tests."""
    return os.getenv("LLM_PROVIDER", "fake")


def get_llm_model() -> str:
    """Default model identifier. Overridden per-agent in production."""
    return os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")


def is_fake_mode() -> bool:
    """True when running with fake/test adapters (no real LLM calls)."""
    return get_llm_provider_name() == "fake"
