from __future__ import annotations

import pytest

from app.agents.orchestrator import AgentOrchestrator, Workflow, WorkflowStep
from app.agents.registry import AgentRegistry
from tests.agents.conftest import AlwaysFailsAgent, AlwaysSucceedsAgent


@pytest.mark.asyncio
async def test_single_stage_workflow_succeeds():
    registry = AgentRegistry()
    registry.register(AlwaysSucceedsAgent())
    orchestrator = AgentOrchestrator(registry)

    workflow = Workflow(
        name="test_workflow",
        stages=[[WorkflowStep(agent_id="always_succeeds", task_type="do_thing")]],
    )
    result = await orchestrator.execute_workflow(workflow, venue_id="venue-1")

    assert result.succeeded
    assert len(result.task_results) == 1
    assert result.task_results[0].succeeded


@pytest.mark.asyncio
async def test_required_step_failure_aborts_workflow():
    registry = AgentRegistry()
    registry.register(AlwaysFailsAgent())
    registry.register(AlwaysSucceedsAgent())
    orchestrator = AgentOrchestrator(registry)

    workflow = Workflow(
        name="test_workflow",
        stages=[
            [WorkflowStep(agent_id="always_fails", task_type="do_thing", required=True)],
            [WorkflowStep(agent_id="always_succeeds", task_type="do_thing")],
        ],
    )
    result = await orchestrator.execute_workflow(workflow, venue_id="venue-1")

    assert result.aborted
    assert not result.succeeded
    # Second stage never ran because the first stage's required step failed.
    assert len(result.task_results) == 1


@pytest.mark.asyncio
async def test_optional_step_failure_does_not_abort_workflow():
    registry = AgentRegistry()
    registry.register(AlwaysFailsAgent())
    registry.register(AlwaysSucceedsAgent())
    orchestrator = AgentOrchestrator(registry)

    workflow = Workflow(
        name="test_workflow",
        stages=[
            [WorkflowStep(agent_id="always_fails", task_type="do_thing", required=False)],
            [WorkflowStep(agent_id="always_succeeds", task_type="do_thing")],
        ],
    )
    result = await orchestrator.execute_workflow(workflow, venue_id="venue-1")

    assert not result.aborted
    assert len(result.task_results) == 2
    assert not result.succeeded  # overall succeeded requires every result to succeed


@pytest.mark.asyncio
async def test_unknown_agent_in_workflow_reports_failure_without_raising():
    registry = AgentRegistry()
    orchestrator = AgentOrchestrator(registry)

    workflow = Workflow(
        name="test_workflow",
        stages=[[WorkflowStep(agent_id="ghost_agent", task_type="do_thing")]],
    )
    result = await orchestrator.execute_workflow(workflow, venue_id="venue-1")

    assert result.aborted
    assert "ghost_agent" in result.abort_reason
