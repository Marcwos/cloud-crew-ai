"""Tests for ResilientLLMProvider — timeout + bounded retry over any provider.

A live demo makes many LLM calls; a transient hiccup must not kill the run.
These tests inject a fake `sleep` so backoff adds no real delay.
"""
from __future__ import annotations

import asyncio

import pytest
from unittest.mock import AsyncMock

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMMessage, LLMResponse


def _request() -> LLMRequest:
    return LLMRequest(
        model="m",
        system="sys",
        messages=[LLMMessage(role="user", content="hi")],
    )


class _FakeAPIError(Exception):
    """Mimics an OpenAI/Anthropic SDK error — carries a status_code."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"status {status_code}")


class _ScriptedLLM:
    """Raises the given exceptions on the first calls, then returns a response."""

    def __init__(self, failures: list[Exception]) -> None:
        self._failures = list(failures)
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return LLMResponse(text="ok", model=request.model)


class TestResilientLLMProvider:
    async def test_retries_transient_error_then_succeeds(self):
        from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider

        inner = _ScriptedLLM([_FakeAPIError(429), _FakeAPIError(503)])
        provider = ResilientLLMProvider(inner, max_attempts=3, sleep=AsyncMock())

        result = await provider.complete(_request())

        assert result.text == "ok"
        assert inner.calls == 3  # two failures + one success

    async def test_permanent_error_fails_fast_without_retry(self):
        from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider

        inner = _ScriptedLLM([_FakeAPIError(401)])
        sleep = AsyncMock()
        provider = ResilientLLMProvider(inner, max_attempts=3, sleep=sleep)

        with pytest.raises(_FakeAPIError):
            await provider.complete(_request())

        assert inner.calls == 1  # 401 is permanent — no retry
        sleep.assert_not_awaited()

    async def test_gives_up_after_max_attempts_on_persistent_transient_error(self):
        from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider

        inner = _ScriptedLLM([_FakeAPIError(500), _FakeAPIError(500), _FakeAPIError(500)])
        provider = ResilientLLMProvider(inner, max_attempts=3, sleep=AsyncMock())

        with pytest.raises(_FakeAPIError):
            await provider.complete(_request())

        assert inner.calls == 3

    async def test_slow_call_times_out_and_is_retryable(self):
        from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider

        class _SlowLLM:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, request: LLMRequest) -> LLMResponse:
                self.calls += 1
                await asyncio.sleep(1.0)  # longer than the timeout below
                return LLMResponse(text="never", model="m")

        inner = _SlowLLM()
        provider = ResilientLLMProvider(inner, timeout_s=0.01, max_attempts=2, sleep=AsyncMock())

        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await provider.complete(_request())

        assert inner.calls == 2  # timeout is transient → retried up to max_attempts

    async def test_success_returns_immediately_without_sleeping(self):
        from src.features.crew.infrastructure.llm.resilient_llm_provider import ResilientLLMProvider

        inner = _ScriptedLLM([])
        sleep = AsyncMock()
        provider = ResilientLLMProvider(inner, sleep=sleep)

        result = await provider.complete(_request())

        assert result.text == "ok"
        assert inner.calls == 1
        sleep.assert_not_awaited()
