"""
Fixtures for agent-framework tests: a fake `LLMClient` (per Module 3's
"Mock LLM provider" testing requirement) and mock `BaseAgent`
implementations covering success, failure, and timeout paths.
"""

from __future__ import annotations

import asyncio

import pytest

from app.agents.base import BaseAgent
from app.agents.observability import AgentMetricsRegistry
from app.agents.types import AgentContext, AgentRequest, StructuredOutput
from app.core.llm_client import LLMClient, LLMResponse


class FakeLLMClient(LLMClient):
    """Deterministic `LLMClient` double — no network, no API key needed."""

    def __init__(self, *, json_response: dict | None = None, text_response: str = "ok") -> None:
        self.json_response = json_response or {"confidence": 0.9}
        self.text_response = text_response
        self.calls: list[str] = []

    async def generate(self, **kwargs) -> LLMResponse:  # noqa: ANN003
        self.calls.append("generate")
        return LLMResponse(text=self.text_response, model="fake-model")

    async def generate_json(self, **kwargs) -> dict:  # noqa: ANN003
        self.calls.append("generate_json")
        return self.json_response


class AlwaysSucceedsAgent(BaseAgent):
    agent_id = "always_succeeds"
    name = "Always Succeeds"
    description = "Test agent that always returns a successful StructuredOutput."
    system_prompt = "You always succeed."
    supported_tasks = ("do_thing",)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.call_count = 0

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        self.call_count += 1
        return StructuredOutput(data={"result": "done"}, confidence=0.8)


class AlwaysFailsAgent(BaseAgent):
    agent_id = "always_fails"
    name = "Always Fails"
    description = "Test agent that always raises."
    system_prompt = "You always fail."
    supported_tasks = ("do_thing",)
    max_retries = 2

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.call_count = 0

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        self.call_count += 1
        raise RuntimeError("simulated failure")


class FailsThenSucceedsAgent(BaseAgent):
    agent_id = "fails_then_succeeds"
    name = "Fails Then Succeeds"
    description = "Test agent that fails once, then succeeds (retry path)."
    system_prompt = "You are flaky."
    supported_tasks = ("do_thing",)
    max_retries = 2

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.call_count = 0

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("transient failure")
        return StructuredOutput(data={"result": "recovered"}, confidence=0.7)


class SlowAgent(BaseAgent):
    agent_id = "slow_agent"
    name = "Slow Agent"
    description = "Test agent that exceeds its timeout."
    system_prompt = "You are slow."
    supported_tasks = ("do_thing",)
    timeout_seconds = 0.05
    max_retries = 0

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        await asyncio.sleep(1.0)
        return StructuredOutput(data={})


@pytest.fixture
def metrics_registry() -> AgentMetricsRegistry:
    return AgentMetricsRegistry()


@pytest.fixture
def fake_llm_client() -> FakeLLMClient:
    return FakeLLMClient()
