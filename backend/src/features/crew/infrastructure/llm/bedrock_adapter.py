"""BedrockAdapter — LLMProvider using Amazon Bedrock via boto3.

Reads AWS credentials from environment or IAM role (standard boto3 resolution).
Model IDs are Bedrock model ARNs (e.g. "anthropic.claude-3-5-haiku-20241022-v1:0").
Tests mock boto3 at import level.

Note: Bedrock uses a different converse API shape. This adapter wraps the
converse API to stay behind the same LLMProvider port.
"""
from __future__ import annotations

import asyncio
import json
import os

try:
    import boto3  # type: ignore[import]
except ImportError:
    boto3 = None  # type: ignore[assignment]

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse


class BedrockAdapter:
    """LLMProvider adapter for Amazon Bedrock (Converse API).

    AWS credentials are resolved via the standard boto3 chain
    (env vars, ~/.aws/credentials, IAM instance role, etc.).
    """

    def __init__(
        self,
        region_name: str | None = None,
    ) -> None:
        if boto3 is None:
            raise ImportError("boto3 package is required. Install with: pip install boto3")
        self._region = region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._client = boto3.client("bedrock-runtime", region_name=self._region)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Invoke a Bedrock model via the Converse API (async wrapper over sync boto3)."""
        messages = [
            {"role": msg.role, "content": [{"text": msg.content}]}
            for msg in request.messages
        ]

        # boto3 is sync — run in thread pool to stay non-blocking
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.converse(
                modelId=request.model,
                system=[{"text": request.system}],
                messages=messages,
                inferenceConfig={
                    "temperature": request.temperature,
                    "maxTokens": request.max_tokens,
                },
            ),
        )

        text = response["output"]["message"]["content"][0]["text"]
        return LLMResponse(text=text, model=request.model)
