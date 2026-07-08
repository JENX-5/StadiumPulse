from __future__ import annotations

import pytest

from app.agents.types import AgentRequest, AgentTaskStatus
from tests.agents.conftest import (
    AlwaysFailsAgent,
    AlwaysSucceedsAgent,
    FailsThenSucceedsAgent,
    SlowAgent,
)


@pytest.mark.asyncio
async def test_successful_execution_returns_succeeded_status(metrics_registry):
    agent = AlwaysSucceedsAgent(metrics=metrics_registry)
    response = await agent.execute(AgentRequest(task_type="do_thing"))

    assert response.status == AgentTaskStatus.SUCCEEDED
    assert response.output is not None
    assert response.output.data == {"result": "done"}
    assert response.attempts == 1


@pytest.mark.asyncio
async def test_unsupported_task_type_fails_validation_without_calling_execute(metrics_registry):
    agent = AlwaysSucceedsAgent(metrics=metrics_registry)
    response = await agent.execute(AgentRequest(task_type="unsupported_task"))

    assert response.status == AgentTaskStatus.FAILED
    assert agent.call_count == 0
    assert "does not support" in response.error_message


@pytest.mark.asyncio
async def test_retries_on_transient_failure_then_succeeds(metrics_registry):
    agent = FailsThenSucceedsAgent(metrics=metrics_registry)
    response = await agent.execute(AgentRequest(task_type="do_thing"))

    assert response.status == AgentTaskStatus.SUCCEEDED
    assert agent.call_count == 2
    assert response.attempts == 2


@pytest.mark.asyncio
async def test_exhausts_retries_and_reports_failure(metrics_registry):
    agent = AlwaysFailsAgent(metrics=metrics_registry)
    response = await agent.execute(AgentRequest(task_type="do_thing"))

    assert response.status == AgentTaskStatus.FAILED
    # max_retries=2 means 3 total attempts.
    assert agent.call_count == 3
    assert response.attempts == 3


@pytest.mark.asyncio
async def test_timeout_is_reported_and_not_retried(metrics_registry):
    agent = SlowAgent(metrics=metrics_registry)
    response = await agent.execute(AgentRequest(task_type="do_thing"))

    assert response.status == AgentTaskStatus.TIMED_OUT


@pytest.mark.asyncio
async def test_metrics_are_recorded_after_execution(metrics_registry):
    agent = AlwaysSucceedsAgent(metrics=metrics_registry)
    await agent.execute(AgentRequest(task_type="do_thing"))
    await agent.execute(AgentRequest(task_type="do_thing"))

    snapshot = metrics_registry.snapshot(agent.agent_id)
    assert snapshot.total_executions == 2
    assert snapshot.total_failures == 0
    assert snapshot.success_rate == 1.0


@pytest.mark.asyncio
async def test_health_check_reports_supported_tasks(metrics_registry):
    agent = AlwaysSucceedsAgent(metrics=metrics_registry)
    health = await agent.health_check()

    assert health["healthy"] is True
    assert health["supported_tasks"] == ["do_thing"]


def test_agent_without_agent_id_raises_at_construction():
    class NoIdAgent(AlwaysSucceedsAgent):
        agent_id = ""

    with pytest.raises(ValueError):
        NoIdAgent()
