"""
Shared LLM client abstraction.

Lives in `core/` (Critical Fix: LLM client location) rather than inside
`agents/`, because Incident Analysis, Predictive Intelligence (narrative
step), Resource Coordination, Operational Consensus, and Tournament Memory
all depend on the same interface. Keeping a single implementation here
means:

  - One place to swap providers (the interface is provider-agnostic).
  - One place to enforce strict JSON schema validation + one corrective
    retry (Critical Fix #4) instead of five ad-hoc implementations.
  - One place to apply timeouts and structured logging for every LLM call
    in the system.

This module intentionally does NOT contain any agent-specific prompts,
scoring logic, or negotiation logic — those belong to `agents/`. This is
transport + reliability plumbing only.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import structlog
from anthropic import APIError, APITimeoutError, AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.core.config import Settings
from app.core.exceptions import LLMClientError

logger = structlog.get_logger(__name__)


class LLMResponse:
    """Normalized response returned by every LLMClient implementation."""

    __slots__ = ("text", "model", "raw")

    def __init__(self, text: str, model: str, raw: Any = None) -> None:
        self.text = text
        self.model = model
        self.raw = raw


class LLMClient(ABC):
    """Provider-agnostic interface every agent depends on.

    Agents type-hint against this class, never against a concrete provider
    client, so the underlying model/vendor can change without touching
    agent code (see docs/decisions/0003 for the vendor-risk rationale).
    """

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Return a single free-text completion."""

    @abstractmethod
    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Return a parsed JSON object.

        Implementations must enforce strict JSON validation and perform
        exactly one automatic corrective retry (re-prompting with a
        "return ONLY valid JSON" follow-up) before raising `LLMClientError`.
        Callers (agents) are responsible for the documented rule-based
        fallback once this raises — this method never silently invents data.
        """


class AnthropicLLMClient(LLMClient):
    """Anthropic-backed implementation of `LLMClient`."""

    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            logger.warning("llm_client_initialized_without_api_key")
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_seconds,
        )
        self._default_model = settings.anthropic_model_default
        self._escalation_model = settings.anthropic_model_escalation
        self._max_retries = settings.llm_max_retries

    @retry(
        retry=retry_if_exception_type((APITimeoutError, APIError)),
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        reraise=True,
    )
    async def _complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> Any:
        return await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

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
        try:
            response = await self._complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=resolved_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except (APITimeoutError, APIError) as exc:
            logger.error("llm_generate_failed", model=resolved_model, error=str(exc))
            raise LLMClientError(f"LLM call failed: {exc}") from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(text=text, model=resolved_model, raw=response)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        resolved_model = model or self._default_model
        json_system_prompt = (
            f"{system_prompt}\n\n"
            "Respond with ONLY a single valid JSON object. "
            "No prose, no markdown code fences, no explanation."
        )

        response = await self.generate(
            system_prompt=json_system_prompt,
            user_prompt=user_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        parsed = self._try_parse_json(response.text)
        if parsed is not None:
            return parsed

        # Exactly one corrective retry, per Critical Fix #4.
        logger.warning("llm_json_parse_failed_retrying", model=resolved_model)
        corrective_prompt = (
            f"{user_prompt}\n\n"
            "Your previous response was not valid JSON. "
            "Return ONLY a single valid JSON object, with no other text."
        )
        retry_response = await self.generate(
            system_prompt=json_system_prompt,
            user_prompt=corrective_prompt,
            model=resolved_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        parsed = self._try_parse_json(retry_response.text)
        if parsed is not None:
            return parsed

        logger.error("llm_json_parse_failed_after_retry", model=resolved_model)
        raise LLMClientError(
            "LLM did not return valid JSON after one corrective retry.",
            details={"raw_response": retry_response.text[:500]},
        )

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        cleaned = (
            text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        )
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return result if isinstance(result, dict) else None
