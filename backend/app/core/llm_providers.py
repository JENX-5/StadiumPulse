"""
Multi-provider LLM layer (Module 3).

`app.core.llm_client` already defines the provider-agnostic `LLMClient`
interface and the original `AnthropicLLMClient` (ADR-0003). This module
adds the remaining pieces the Agent Framework spec calls for without
touching that file's existing contract:

  - `OpenAILLMClient` / `GeminiLLMClient` — alternative implementations of
    the same `LLMClient` interface.
  - `RateLimitedLLMClient` — a decorator over any `LLMClient` that enforces
    a requests-per-minute budget, so rate limiting is applied uniformly
    regardless of which provider is active instead of being duplicated
    inside each provider implementation.
  - `build_llm_client(settings)` — the Factory Pattern entrypoint. This is
    the one function `Container` calls; nothing else in the codebase should
    import a concrete provider class directly.

Local models are listed in the spec as "future" — `LocalLLMClient` is a
deliberate stub that raises `NotImplementedError` so the factory's provider
set is already complete and callers get a clear error rather than a
silent no-op if it's selected before it's implemented.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque

import structlog

from app.core.config import Settings
from app.core.exceptions import LLMClientError
from app.core.llm_client import AnthropicLLMClient, LLMClient, LLMResponse

logger = structlog.get_logger(__name__)


class OpenAILLMClient(LLMClient):
    """OpenAI-backed implementation of `LLMClient`."""

    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI  # local import: optional dependency

        if not settings.openai_api_key:
            logger.warning("llm_client_initialized_without_api_key", provider="openai")
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds
        )
        self._default_model = settings.openai_model_default
        self._max_retries = settings.llm_max_retries

    async def _complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001 - normalized below
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(1)
        logger.error("llm_generate_failed", model=model, error=str(last_error), provider="openai")
        raise LLMClientError(f"OpenAI call failed: {last_error}") from last_error

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        resolved_model = model or self._default_model
        text = await self._complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return LLMResponse(text=text, model=resolved_model)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict:
        resolved_model = model or self._default_model
        json_system_prompt = (
            f"{system_prompt}\n\nRespond with ONLY a single valid JSON object. "
            "No prose, no markdown code fences, no explanation."
        )
        text = await self._complete(
            system_prompt=json_system_prompt,
            user_prompt=user_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        parsed = _try_parse_json(text)
        if parsed is not None:
            return parsed

        logger.warning("llm_json_parse_failed_retrying", model=resolved_model, provider="openai")
        corrective = f"{user_prompt}\n\nYour previous response was not valid JSON. Return ONLY a single valid JSON object."
        text = await self._complete(
            system_prompt=json_system_prompt,
            user_prompt=corrective,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        parsed = _try_parse_json(text)
        if parsed is not None:
            return parsed
        raise LLMClientError(
            "OpenAI did not return valid JSON after one corrective retry.",
            details={"raw_response": text[:500]},
        )


class GeminiLLMClient(LLMClient):
    """Gemini-backed implementation of `LLMClient` (via the `google-genai` SDK)."""

    def __init__(self, settings: Settings) -> None:
        from google import genai  # local import: optional dependency

        if not settings.gemini_api_key:
            logger.warning("llm_client_initialized_without_api_key", provider="gemini")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._default_model = settings.gemini_model_default
        self._max_retries = settings.llm_max_retries
        self._timeout = settings.llm_timeout_seconds

    async def _complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        is_json: bool = False,
    ) -> str:
        from google.genai import types

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                config_kwargs = {
                    "system_instruction": system_prompt,
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                }
                if is_json:
                    config_kwargs["response_mime_type"] = "application/json"
                    
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(**config_kwargs),
                    ),
                    timeout=self._timeout,
                )
                return response.text or ""
            except Exception as exc:  # noqa: BLE001 - normalized below
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(1)
        logger.error("llm_generate_failed", model=model, error=str(last_error), provider="gemini")
        raise LLMClientError(f"Gemini call failed: {last_error}") from last_error

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        resolved_model = model or self._default_model
        text = await self._complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return LLMResponse(text=text, model=resolved_model)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict:
        resolved_model = model or self._default_model
        json_system_prompt = (
            f"{system_prompt}\n\nRespond with ONLY a single valid JSON object. "
            "No prose, no markdown code fences, no explanation."
        )
        text = await self._complete(
            system_prompt=json_system_prompt,
            user_prompt=user_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
            is_json=True,
        )
        parsed = _try_parse_json(text)
        if parsed is not None:
            return parsed

        logger.warning("llm_json_parse_failed_retrying", model=resolved_model, provider="gemini")
        corrective = f"{user_prompt}\n\nYour previous response was not valid JSON. Return ONLY a single valid JSON object."
        text = await self._complete(
            system_prompt=json_system_prompt,
            user_prompt=corrective,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
            is_json=True,
        )
        parsed = _try_parse_json(text)
        if parsed is not None:
            return parsed
        raise LLMClientError(
            "Gemini did not return valid JSON after one corrective retry.",
            details={"raw_response": text[:500]},
        )


class LocalLLMClient(LLMClient):
    """Placeholder for a future locally-hosted model (spec: 'Local Models (future)')."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, **kwargs) -> LLMResponse:  # noqa: ANN003
        raise NotImplementedError("Local model provider is not implemented yet.")

    async def generate_json(self, **kwargs) -> dict:  # noqa: ANN003
        raise NotImplementedError("Local model provider is not implemented yet.")


class RateLimitedLLMClient(LLMClient):
    """Wraps any `LLMClient` with a sliding-window requests-per-minute budget.

    Applied once by the factory rather than inside each provider so every
    provider gets identical rate-limiting behavior. Uses an in-process
    sliding window (a deque of call timestamps) — sufficient for a single
    backend instance; a multi-instance deployment would need a shared
    (e.g. Redis-backed) limiter instead, noted here rather than built now
    since only one instance runs at hackathon/tournament scale.
    """

    def __init__(self, wrapped: LLMClient, *, requests_per_minute: int) -> None:
        self._wrapped = wrapped
        self._limit = max(requests_per_minute, 1)
        self._window_seconds = 60.0
        self._call_times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def _acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._call_times and now - self._call_times[0] > self._window_seconds:
                self._call_times.popleft()
            if len(self._call_times) >= self._limit:
                wait_for = self._window_seconds - (now - self._call_times[0])
                logger.warning("llm_rate_limit_wait", seconds=round(wait_for, 2))
                await asyncio.sleep(max(wait_for, 0))
                now = time.monotonic()
                while self._call_times and now - self._call_times[0] > self._window_seconds:
                    self._call_times.popleft()
            self._call_times.append(now)

    async def generate(self, **kwargs) -> LLMResponse:  # noqa: ANN003
        await self._acquire()
        return await self._wrapped.generate(**kwargs)

    async def generate_json(self, **kwargs) -> dict:  # noqa: ANN003
        await self._acquire()
        return await self._wrapped.generate_json(**kwargs)


def _try_parse_json(text: str) -> dict | None:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return result if isinstance(result, dict) else None


_PROVIDER_BUILDERS = {
    "anthropic": AnthropicLLMClient,
    "openai": OpenAILLMClient,
    "gemini": GeminiLLMClient,
    "local": LocalLLMClient,
}


def build_llm_client(settings: Settings) -> LLMClient:
    """Factory: construct the configured provider's `LLMClient`, rate-limited.

    This is the single call site every part of the app should use to obtain
    an `LLMClient` (see `Container.llm_client`) — never instantiate a
    concrete provider class directly outside this function.
    """
    builder = _PROVIDER_BUILDERS.get(settings.llm_provider)
    if builder is None:
        raise LLMClientError(f"Unknown LLM provider configured: {settings.llm_provider!r}")

    client = builder(settings)
    logger.info("llm_client_built", provider=settings.llm_provider)
    return RateLimitedLLMClient(client, requests_per_minute=settings.llm_rate_limit_per_minute)
