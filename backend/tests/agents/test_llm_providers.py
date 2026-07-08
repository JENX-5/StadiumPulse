from __future__ import annotations

import time

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient, LLMResponse
from app.core.llm_providers import (
    GeminiLLMClient,
    OpenAILLMClient,
    RateLimitedLLMClient,
    build_llm_client,
)


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_factory_builds_anthropic_by_default():
    client = build_llm_client(_settings())
    assert isinstance(client, RateLimitedLLMClient)


def test_factory_builds_openai_client():
    client = build_llm_client(_settings(LLM_PROVIDER="openai", OPENAI_API_KEY="sk-test"))
    assert isinstance(client, RateLimitedLLMClient)
    assert isinstance(client._wrapped, OpenAILLMClient)


def test_factory_builds_gemini_client():
    client = build_llm_client(_settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="test-key"))
    assert isinstance(client._wrapped, GeminiLLMClient)


def test_factory_rejects_unknown_provider():
    settings = _settings()
    object.__setattr__(settings, "llm_provider", "made_up_provider")
    with pytest.raises(LLMClientError):
        build_llm_client(settings)


class _CountingLLMClient(LLMClient):
    def __init__(self) -> None:
        self.call_count = 0

    async def generate(self, **kwargs):  # noqa: ANN003
        self.call_count += 1
        return LLMResponse(text="ok", model="fake")

    async def generate_json(self, **kwargs):  # noqa: ANN003
        self.call_count += 1
        return {}


@pytest.mark.asyncio
async def test_rate_limited_client_allows_calls_within_budget():
    inner = _CountingLLMClient()
    limited = RateLimitedLLMClient(inner, requests_per_minute=5)

    for _ in range(5):
        await limited.generate(system_prompt="s", user_prompt="u")

    assert inner.call_count == 5


@pytest.mark.asyncio
async def test_rate_limited_client_throttles_beyond_budget():
    inner = _CountingLLMClient()
    # Small window budget forces the 3rd call to wait.
    limited = RateLimitedLLMClient(inner, requests_per_minute=2)
    limited._window_seconds = 0.2  # shrink window so the test runs fast

    start = time.monotonic()
    await limited.generate(system_prompt="s", user_prompt="u")
    await limited.generate(system_prompt="s", user_prompt="u")
    await limited.generate(system_prompt="s", user_prompt="u")  # should wait ~0.2s
    elapsed = time.monotonic() - start

    assert inner.call_count == 3
    assert elapsed >= 0.15
