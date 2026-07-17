"""
BaseAgent: the reusable lifecycle every concrete agent (Predictive
Intelligence, Incident Analysis, Resource Coordination, Operational
Consensus, Tournament Memory — all future modules) inherits from.

This class owns everything that would otherwise be duplicated five times:
input/output validation, retry-with-timeout execution, confidence
extraction, structured logging, and metrics. Concrete subclasses implement
only `_execute()` — the actual reasoning/prompting/business logic — which
this module intentionally does NOT provide (per Module 3's scope: no
business intelligence yet).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import structlog

from app.agents.exceptions import (
    AgentTimeoutError,
    AgentValidationError,
)
from app.agents.observability import AgentMetricsRegistry, TokenUsage
from app.agents.types import (
    AgentContext,
    AgentRequest,
    AgentResponse,
    AgentTaskStatus,
    StructuredOutput,
)

logger = structlog.get_logger(__name__)

# Shared default registry so agents get metrics/tracing without every
# caller having to thread one through by hand. `Container`/tests can still
# inject a dedicated instance via the constructor when isolation matters.
_default_metrics_registry = AgentMetricsRegistry()


class BaseAgent(ABC):
    """Abstract base every concrete agent implementation subclasses.

    Subclasses must set `agent_id`, `name`, `description`, `system_prompt`,
    and `supported_tasks`, and implement `_execute()`. Everything else
    (`execute()`'s lifecycle, retries, timeouts, validation, metrics) is
    provided here and should not be overridden except in unusual cases.
    """

    agent_id: str
    name: str
    description: str
    system_prompt: str
    supported_tasks: tuple[str, ...] = ()

    max_retries: int = 1
    timeout_seconds: float = 30.0

    def __init__(self, *, metrics: AgentMetricsRegistry | None = None) -> None:
        if not getattr(self, "agent_id", None):
            raise ValueError(f"{type(self).__name__} must set a non-empty agent_id")
        self._metrics = metrics or _default_metrics_registry
        self._logger = logger.bind(agent_id=self.agent_id)

    # -- Lifecycle ------------------------------------------------------

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Full execution lifecycle: validate -> run (retry + timeout) ->
        validate output -> record metrics -> return a normalized response.

        This never raises for expected failure modes (validation failure,
        execution failure, timeout) — those are reported as a `FAILED` /
        `TIMED_OUT` `AgentResponse` so the orchestrator can decide how to
        handle a partial workflow failure. Programmer errors (bugs) still
        propagate.
        """
        trace = self._metrics.start_trace(self.agent_id, request.task_type)
        started = datetime.now(timezone.utc)
        attempts = 0

        try:
            self.validate_input(request)
        except AgentValidationError as exc:
            self._metrics.finish_trace(trace, success=False, error_message=exc.message)
            return self._response(
                request,
                AgentTaskStatus.FAILED,
                error_message=exc.message,
                attempts=0,
                started=started,
            )

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            attempts = attempt
            try:
                output = await asyncio.wait_for(
                    self._execute(request, request.context), timeout=self.timeout_seconds
                )
                self.validate_output(output)
                self._metrics.finish_trace(trace, success=True, tokens=self._extract_tokens(output))
                return self._response(
                    request,
                    AgentTaskStatus.SUCCEEDED,
                    output=output,
                    attempts=attempts,
                    started=started,
                )
            except TimeoutError:
                last_error = AgentTimeoutError(
                    f"Agent '{self.agent_id}' timed out after {self.timeout_seconds}s"
                )
                self._logger.warning("agent_execution_timeout", attempt=attempt)
                break  # a timeout is not retried — retrying a slow call rarely helps
            except AgentValidationError as exc:
                last_error = exc
                self._logger.warning(
                    "agent_output_validation_failed", attempt=attempt, error=exc.message
                )
                break  # bad output is a bug in this attempt, not a transient fault
            except Exception as exc:  # noqa: BLE001 - normalized into AgentExecutionError
                last_error = exc
                self._logger.warning(
                    "agent_execution_attempt_failed", attempt=attempt, error=str(exc)
                )
                if attempt <= self.max_retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), 5))

        status = (
            AgentTaskStatus.TIMED_OUT
            if isinstance(last_error, AgentTimeoutError)
            else AgentTaskStatus.FAILED
        )
        error_message = str(last_error) if last_error else "Unknown agent execution failure"
        self._metrics.finish_trace(trace, success=False, error_message=error_message)
        return self._response(
            request, status, error_message=error_message, attempts=attempts, started=started
        )

    # -- Hooks subclasses may override -----------------------------------

    def validate_input(self, request: AgentRequest) -> None:
        """Default: confirm the task_type is one this agent supports.

        Subclasses typically extend this to also validate `input_data`
        shape (e.g. via a Pydantic model specific to that task type).
        """
        if self.supported_tasks and request.task_type not in self.supported_tasks:
            raise AgentValidationError(
                f"Agent '{self.agent_id}' does not support task_type '{request.task_type}'",
                details={"supported_tasks": list(self.supported_tasks)},
            )

    def validate_output(self, output: StructuredOutput) -> None:
        """Default: rely on `StructuredOutput`'s own Pydantic validation
        (confidence bounds, etc). Subclasses override to also validate
        `output.data` against a task-specific schema."""
        if not isinstance(output, StructuredOutput):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' must return a StructuredOutput, got {type(output).__name__}"
            )

    @abstractmethod
    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        """The agent's actual work. Implemented by concrete agent modules —
        deliberately not implemented here (Module 3 is infrastructure only)."""

    async def health_check(self) -> dict[str, object]:
        """Cheap self-report used by the registry's health status API.

        Subclasses with an external dependency (LLM call, DB, etc.) should
        override this to actually probe that dependency; the default just
        confirms the agent is constructed and reports its recent metrics.
        """
        snapshot = self._metrics.snapshot(self.agent_id)
        return {
            "agent_id": self.agent_id,
            "healthy": True,
            "supported_tasks": list(self.supported_tasks),
            "success_rate": snapshot.success_rate,
            "average_duration_ms": snapshot.average_duration_ms,
        }

    # -- Internals --------------------------------------------------------

    def _response(
        self,
        request: AgentRequest,
        status: AgentTaskStatus,
        *,
        output: StructuredOutput | None = None,
        error_message: str | None = None,
        attempts: int,
        started: datetime,
    ) -> AgentResponse:
        duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
        return AgentResponse(
            request_id=request.request_id,
            agent_id=self.agent_id,
            status=status,
            output=output,
            error_message=error_message,
            duration_ms=duration_ms,
            attempts=attempts,
        )

    @staticmethod
    def _extract_tokens(output: StructuredOutput) -> TokenUsage | None:
        usage = output.data.get("_token_usage") if isinstance(output.data, dict) else None
        if not usage:
            return None
        return TokenUsage(
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
