"""
AgentOrchestrator: the heart of the AI system (per Module 3's spec).

Executes a `Workflow` (an ordered list of steps, each naming an agent_id +
task_type) against the `AgentRegistry`, threading a single
`SharedContextManager` through every step so later agents see earlier
agents' outputs.

Only sequential execution is implemented, but `WorkflowStep` groups are
already structured as "stages" (a list of stages, each stage a list of
steps) specifically so a future change can execute the steps *within* a
stage concurrently via `asyncio.gather` without changing the `Workflow`
data shape or any caller code — only `_run_stage`'s body would change.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import structlog

from app.agents.context import SharedContextManager
from app.agents.exceptions import AgentNotFoundError
from app.agents.registry import AgentRegistry
from app.agents.types import AgentRequest, AgentTaskStatus, TaskResult

logger = structlog.get_logger(__name__)


@dataclass(slots=True, frozen=True)
class WorkflowStep:
    """One agent invocation within a workflow stage."""

    agent_id: str
    task_type: str
    input_data: dict = field(default_factory=dict)
    # If True, a failure here aborts the remaining workflow instead of
    # continuing to the next stage with a partial result.
    required: bool = True


@dataclass(slots=True)
class Workflow:
    """An ordered list of stages. Today, every stage's steps run
    sequentially and stages run sequentially — see module docstring for
    why stages are already broken out for future parallel execution."""

    name: str
    stages: list[list[WorkflowStep]]


@dataclass(slots=True)
class WorkflowResult:
    workflow_name: str
    task_results: list[TaskResult]
    aborted: bool = False
    abort_reason: str | None = None

    @property
    def succeeded(self) -> bool:
        return not self.aborted and all(r.succeeded for r in self.task_results)


class AgentOrchestrator:
    """Coordinates multi-agent workflows: looks agents up in the registry,
    executes them against a shared context, and aggregates results."""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    async def execute_workflow(
        self, workflow: Workflow, *, venue_id: str, incident_id: str | None = None
    ) -> WorkflowResult:
        context_manager = SharedContextManager(venue_id=venue_id, incident_id=incident_id)
        task_results: list[TaskResult] = []
        step_index = 0

        for stage in workflow.stages:
            stage_results = await self._run_stage(stage, context_manager, step_index)
            task_results.extend(stage_results)
            step_index += len(stage)

            for step, result in zip(stage, stage_results, strict=True):
                if step.required and not result.succeeded:
                    logger.warning(
                        "workflow_aborted",
                        workflow=workflow.name,
                        agent_id=step.agent_id,
                        error=result.error_message,
                    )
                    return WorkflowResult(
                        workflow_name=workflow.name,
                        task_results=task_results,
                        aborted=True,
                        abort_reason=(
                            f"Required step '{step.agent_id}:{step.task_type}' failed: "
                            f"{result.error_message}"
                        ),
                    )
                # A successful step's output is made available to later
                # stages under a predictable key so downstream agents don't
                # need to know each other's task_types ahead of time.
                if result.succeeded and result.response and result.response.output:
                    context_manager.set_shared_variable(
                        f"{step.agent_id}:{step.task_type}", result.response.output.model_dump()
                    )

        return WorkflowResult(workflow_name=workflow.name, task_results=task_results)

    async def _run_stage(
        self, stage: list[WorkflowStep], context_manager: SharedContextManager, start_index: int
    ) -> list[TaskResult]:
        """Executes all steps in a stage concurrently.
        Safe to parallelize because every step in a stage shares the same context snapshot."""
        tasks = [
            self._run_step(step, context_manager, step_index=start_index + offset)
            for offset, step in enumerate(stage)
        ]
        return await asyncio.gather(*tasks)

    async def _run_step(
        self, step: WorkflowStep, context_manager: SharedContextManager, *, step_index: int
    ) -> TaskResult:
        try:
            agent = self._registry.get(step.agent_id)
        except AgentNotFoundError as exc:
            return TaskResult(
                step_index=step_index,
                agent_id=step.agent_id,
                task_type=step.task_type,
                error_message=exc.message,
            )

        request = AgentRequest(
            task_type=step.task_type,
            input_data=step.input_data,
            context=context_manager.context,
        )
        response = await agent.execute(request)
        error_message = (
            response.error_message if response.status != AgentTaskStatus.SUCCEEDED else None
        )
        return TaskResult(
            step_index=step_index,
            agent_id=step.agent_id,
            task_type=step.task_type,
            response=response,
            error_message=error_message,
        )
