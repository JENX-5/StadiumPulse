"""
Observability for the agent framework: per-agent execution metrics,
lightweight execution tracing, and token-usage tracking.

Kept in-process (no external metrics backend wired up yet) — this gives
every agent consistent counters/timing for free via `BaseAgent`, and the
snapshot/trace shapes are stable so a later module can ship them to
Prometheus/OTel without changing any call sites in `agents/`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import timezone, datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class AgentMetricsSnapshot:
    agent_id: str
    total_executions: int = 0
    total_failures: int = 0
    total_duration_ms: float = 0.0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 1.0
        return (self.total_executions - self.total_failures) / self.total_executions

    @property
    def average_duration_ms(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_duration_ms / self.total_executions


@dataclass(slots=True)
class ExecutionTrace:
    """One recorded execution, for the demo-facing 'why did this happen'
    trail as well as debugging."""

    trace_id: str
    agent_id: str
    task_type: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    error_message: str | None = None

    @property
    def duration_ms(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds() * 1000


class AgentMetricsRegistry:
    """Process-wide store of per-agent metrics and recent execution traces.

    Not thread-safe by design (the app is single-process asyncio) — a
    dict keyed by agent_id is sufficient here.
    """

    def __init__(self, *, max_traces_per_agent: int = 200) -> None:
        self._metrics: dict[str, AgentMetricsSnapshot] = {}
        self._traces: dict[str, list[ExecutionTrace]] = {}
        self._max_traces = max_traces_per_agent

    def start_trace(self, agent_id: str, task_type: str) -> ExecutionTrace:
        trace = ExecutionTrace(
            trace_id=str(uuid.uuid4()),
            agent_id=agent_id,
            task_type=task_type,
            started_at=datetime.now(timezone.utc),
        )
        self._traces.setdefault(agent_id, []).append(trace)
        traces = self._traces[agent_id]
        if len(traces) > self._max_traces:
            del traces[: len(traces) - self._max_traces]
        return trace

    def finish_trace(
        self,
        trace: ExecutionTrace,
        *,
        success: bool,
        error_message: str | None = None,
        tokens: TokenUsage | None = None,
    ) -> None:
        trace.finished_at = datetime.now(timezone.utc)
        trace.status = "succeeded" if success else "failed"
        trace.error_message = error_message

        snapshot = self._metrics.setdefault(
            trace.agent_id, AgentMetricsSnapshot(agent_id=trace.agent_id)
        )
        snapshot.total_executions += 1
        if not success:
            snapshot.total_failures += 1
        if trace.duration_ms is not None:
            snapshot.total_duration_ms += trace.duration_ms
        if tokens is not None:
            snapshot.total_tokens += tokens.total_tokens

        logger.info(
            "agent_execution_recorded",
            agent_id=trace.agent_id,
            task_type=trace.task_type,
            status=trace.status,
            duration_ms=trace.duration_ms,
        )

    def snapshot(self, agent_id: str) -> AgentMetricsSnapshot:
        return self._metrics.get(agent_id, AgentMetricsSnapshot(agent_id=agent_id))

    def recent_traces(self, agent_id: str, limit: int = 20) -> list[ExecutionTrace]:
        return list(self._traces.get(agent_id, []))[-limit:]

    def all_snapshots(self) -> dict[str, AgentMetricsSnapshot]:
        return dict(self._metrics)


class Timer:
    """Tiny context-manager stopwatch, avoids repeating `time.perf_counter()` pairs."""

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
