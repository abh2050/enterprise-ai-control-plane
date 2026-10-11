"""Google GenAI provider for Gemini on Vertex AI or the Gemini Developer API.

One client class serves both backends through google-genai:
- ``vertex``: Vertex AI, authenticated with application default credentials.
- ``gemini_api``: Gemini Developer API (AI Studio), authenticated with an API key.

The SDK retry layer is disabled (one attempt), the request deadline is enforced by the
HTTP client, and thinking is set to its minimum. Logs never include prompts or
message text.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from control_plane.contracts import Provenance
from control_plane.providers.base import (
    CacheHandle,
    ProviderRejectedError,
    ProviderResponse,
    ProviderTimeoutError,
    TokenCount,
)

log = logging.getLogger(__name__)

# Vertex pricing page (checked 2026-10-11): "You're charged only for requests that return
# a 200 response code. Requests returning any other response codes, such as 4xx and 5xx
# codes, aren't charged." So any error response releases the reservation. Only a lost
# response (timeout or dropped connection) leaves the outcome unknown.


class GenAIProvider:
    provenance = Provenance.MEASURED

    def __init__(
        self,
        backend: str,
        *,
        api_key: str | None = None,
        project: str | None = None,
        location: str | None = None,
        thinking_level: str = "minimal",
    ) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self.backend = backend
        self.thinking_level = thinking_level
        no_retry = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        if backend == "vertex":
            self._client = genai.Client(
                vertexai=True, project=project, location=location, http_options=no_retry
            )
        elif backend == "gemini_api":
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for the gemini_api backend")
            self._client = genai.Client(api_key=api_key, http_options=no_retry)
        else:
            raise ValueError(f"unknown backend {backend}")

    def count_tokens(
        self, model_id: str, prompt: str, response_schema: dict[str, Any] | None = None
    ) -> TokenCount:
        config = None
        if response_schema is not None and self.backend == "vertex":
            # Counting with the schema gets closer to billed input. Structured output still
            # adds a small fixed overhead the count omits; the output cap in each
            # reservation covers it, and the pilot reports counted versus billed tokens.
            config = self._types.CountTokensConfig(
                generation_config=self._types.GenerationConfig(
                    response_mime_type="application/json", response_json_schema=response_schema
                )
            )
        resp = self._client.models.count_tokens(model=model_id, contents=prompt, config=config)
        return TokenCount(input_tokens=int(resp.total_tokens or 0))

    def generate_structured(
        self,
        model_id: str,
        prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        deadline_seconds: float,
        cached_content: str | None = None,
    ) -> ProviderResponse:
        from google.genai import errors

        types = self._types
        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_json_schema=response_schema,
            thinking_config=types.ThinkingConfig(thinking_level=self.thinking_level),
            cached_content=cached_content,
            http_options=types.HttpOptions(
                timeout=int(deadline_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        started = time.perf_counter()
        try:
            resp = self._client.models.generate_content(
                model=model_id, contents=prompt, config=config
            )
        except errors.APIError as exc:
            raise ProviderRejectedError(exc.code, exc.status or "error response") from exc
        except Exception as exc:  # timeouts and dropped connections from the HTTP layer
            if _is_timeout(exc):
                raise ProviderTimeoutError("deadline passed after send") from exc
            raise
        latency_ms = round((time.perf_counter() - started) * 1000)

        usage = resp.usage_metadata
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        candidate_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        thinking_tokens = int(getattr(usage, "thoughts_token_count", 0) or 0)
        cached_tokens = int(getattr(usage, "cached_content_token_count", 0) or 0)
        finish = None
        if resp.candidates and resp.candidates[0].finish_reason is not None:
            finish = str(resp.candidates[0].finish_reason.name)
        output: dict[str, Any] | None
        try:
            parsed = json.loads(resp.text or "")
            output = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            output = None
        log.info(
            "genai call model=%s latency_ms=%d in=%d out=%d think=%d cached=%d finish=%s",
            model_id,
            latency_ms,
            prompt_tokens,
            candidate_tokens,
            thinking_tokens,
            cached_tokens,
            finish,
        )
        return ProviderResponse(
            output=output,
            input_tokens=prompt_tokens,
            output_tokens=candidate_tokens + thinking_tokens,
            latency_ms=latency_ms,
            model_id=model_id,
            provenance=Provenance.MEASURED,
            cached_tokens=cached_tokens,
            thinking_tokens=thinking_tokens,
            finish_reason=finish,
        )


def create_cache(
    provider: GenAIProvider, model_id: str, prefix: str, ttl_seconds: int, label: str
) -> CacheHandle:
    """Store a fixed prompt prefix as an explicit context cache."""
    types = provider._types
    cache = provider._client.caches.create(
        model=model_id,
        config=types.CreateCachedContentConfig(
            contents=[prefix], ttl=f"{ttl_seconds}s", display_name=label[:120]
        ),
    )
    tokens = int(cache.usage_metadata.total_token_count or 0) if cache.usage_metadata else 0
    expires = cache.expire_time.timestamp() if cache.expire_time else time.time() + ttl_seconds
    return CacheHandle(str(cache.name), model_id, tokens, expires)


def delete_cache(provider: GenAIProvider, name: str) -> None:
    provider._client.caches.delete(name=name)


def _is_timeout(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    return "timeout" in name or "timedout" in name or "readerror" in name


# Kept for the Section 3 layout: the Vertex provider is this class with backend="vertex".
VertexProvider = GenAIProvider
