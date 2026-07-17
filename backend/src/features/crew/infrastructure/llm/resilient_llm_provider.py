"""ResilientLLMProvider — wraps any LLMProvider with a timeout and bounded retry.

A live crew session makes 7-8 LLM calls; a single transient hiccup (a 429 rate
limit, a 5xx, a slow response) would otherwise take the whole run down. This
decorator adds a per-call timeout and retries transient failures with
exponential backoff. Permanent errors (401/400) fail fast — retrying them only
burns time. Provider-agnostic: the OpenAI and Anthropic SDK errors both carry a
`status_code`, so we never import a concrete adapter here.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from src.features.crew.domain.ports.llm_provider import LLMProvider, LLMRequest, LLMResponse

# 429 = rate limit, 5xx = server-side — worth retrying. 4xx like 401/400 are
# permanent (bad key, bad request) and must fail fast.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_DEFAULT_TIMEOUT_S = 60.0
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BASE_DELAY_S = 0.5


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    return getattr(exc, "status_code", None) in _RETRYABLE_STATUS


class ResilientLLMProvider:
    """Timeout + exponential-backoff retry decorator over any LLMProvider."""

    def __init__(
        self,
        inner: LLMProvider,
        *,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        base_delay_s: float = _DEFAULT_BASE_DELAY_S,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._inner = inner
        self._timeout_s = timeout_s
        self._max_attempts = max_attempts
        self._base_delay_s = base_delay_s
        self._sleep = sleep  # injectable so tests don't wait on real backoff

    async def complete(self, request: LLMRequest) -> LLMResponse:
        for attempt in range(self._max_attempts):
            try:
                return await asyncio.wait_for(self._inner.complete(request), self._timeout_s)
            except Exception as exc:  # noqa: BLE001 — retry decision made just below
                if attempt == self._max_attempts - 1 or not _is_retryable(exc):
                    raise
                await self._sleep(self._base_delay_s * (2 ** attempt))
        raise AssertionError("unreachable: loop returns or raises on the last attempt")
