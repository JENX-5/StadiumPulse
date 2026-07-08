"""
SharedContextManager: the single source of truth for "what does this
workflow currently know" while an orchestrated multi-agent task runs.

Distinct from `AgentMemory`/Tournament Memory (long-term, cross-incident,
pgvector-backed — a future module): this is short-lived, in-process,
per-workflow-run context. It exists so agent N+1 in a sequential workflow
can see what agent N wrote (e.g. Incident Analysis's structured summary
feeding Predictive Intelligence) without every agent needing to know about
every other agent's output shape directly.
"""

from __future__ import annotations

import copy
from typing import Any

from app.agents.types import AgentContext


class SharedContextManager:
    """Owns one `AgentContext` for the lifetime of a single orchestrated run.

    One instance per workflow execution — this is NOT a process-wide
    singleton (unlike `AgentRegistry`), since context is scoped to one
    incident/workflow at a time and must not leak between concurrent runs.
    """

    def __init__(self, *, venue_id: str, incident_id: str | None = None) -> None:
        self._context = AgentContext(venue_id=venue_id, incident_id=incident_id)
        self._temporary: dict[str, Any] = {}

    @property
    def context(self) -> AgentContext:
        """A defensive copy — callers get a snapshot, not a live handle,
        so they can't mutate shared state except through this manager's
        explicit setters."""
        return self._context.model_copy(deep=True)

    def set_current_incident(self, incident: dict[str, Any]) -> None:
        self._context.current_incident = copy.deepcopy(incident)

    def update_venue_state(self, **fields: Any) -> None:
        self._context.venue_state.update(fields)

    def update_risk_info(self, **fields: Any) -> None:
        self._context.risk_info.update(fields)

    def add_historical_context(self, entry: dict[str, Any]) -> None:
        self._context.historical_context.append(entry)

    def set_shared_variable(self, key: str, value: Any) -> None:
        self._context.shared_variables[key] = value

    def get_shared_variable(self, key: str, default: Any = None) -> Any:
        return self._context.shared_variables.get(key, default)

    # -- Temporary (scratch) memory ---------------------------------------
    # Deliberately separate from `shared_variables`: these are working
    # values an agent stashes mid-workflow (e.g. an intermediate score
    # before the next agent finalizes it) and are expected to be cleared
    # between runs, whereas shared_variables are meant to persist for the
    # life of the AgentContext snapshot handed to every step.

    def set_temporary(self, key: str, value: Any) -> None:
        self._temporary[key] = value

    def get_temporary(self, key: str, default: Any = None) -> Any:
        return self._temporary.get(key, default)

    def clear_temporary(self) -> None:
        self._temporary.clear()

    def snapshot(self) -> dict[str, Any]:
        """Full dump (context + temporary) — useful for logging/debugging
        a workflow run after the fact."""
        return {"context": self._context.model_dump(), "temporary": dict(self._temporary)}
