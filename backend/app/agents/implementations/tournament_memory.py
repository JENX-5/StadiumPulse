"""
Tournament Memory Agent (TMA).

Summarizes a resolved incident into a concise memory payload. This payload
will be converted into an embedding and stored in pgvector (`tournament_memory`)
for future historical pattern matching.

This agent runs asynchronously after the operational consensus is reached
and the incident is effectively closed or handed off.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentValidationError
from app.agents.types import AgentContext, AgentRequest, StructuredOutput
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient

SYSTEM_PROMPT = """You are the Tournament Memory component of a stadium operations platform.
An incident has just been resolved by the system.
Your job is to read the incident details and the final operational consensus decision,
and summarize the event into a concise "memory" paragraph.

This memory will be converted into a vector embedding for semantic similarity searches
in the future, so focus on the key operational facts:
- Incident type and severity
- The core problem or trigger
- The resources dispatched
- The final resolution or action taken

Respond with a JSON object with exactly this key:
- "memory_summary": a concise 1-3 sentence summary of the incident and its resolution.
"""


class TournamentMemoryAgent(BaseAgent):
    agent_id = "tournament_memory"
    name = "Tournament Memory Agent"
    description = (
        "Summarizes resolved incidents into concise operational memories "
        "for semantic vector search."
    )
    system_prompt = SYSTEM_PROMPT
    supported_tasks: tuple[str, ...] = ("generate_memory",)

    max_retries = 1
    # Must exceed the LLM client's own worst-case time, not just typical
    # latency: generate_json can retry twice (llm_max_retries) at up to
    # llm_timeout_seconds each, across up to two calls (initial + one
    # corrective JSON retry) -- ~80s worst case. A shorter timeout here
    # would let asyncio.wait_for (agents/base.py) cancel _execute() before
    # its own try/except ever gets to run the deterministic fallback below,
    # defeating the fallback exactly when the LLM is slow/degraded, which
    # is the one scenario it exists for. (Found via a real degraded-model
    # incident, not speculatively.)
    timeout_seconds = 90.0

    def __init__(self, *, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm = llm_client

    # -- Validation ---------------------------------------------------------

    def validate_input(self, request: AgentRequest) -> None:
        super().validate_input(request)
        data = request.input_data

        if "incident" not in data or not isinstance(data["incident"], dict):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'incident' dictionary in input_data"
            )
        if "decision" not in data or not isinstance(data["decision"], dict):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'decision' dictionary in input_data"
            )

    def validate_output(self, output: StructuredOutput) -> None:
        super().validate_output(output)
        data = output.data
        if not data.get("memory_summary") or not isinstance(data["memory_summary"], str):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid or missing 'memory_summary' string"
            )

    # -- Execution ------------------------------------------------------------

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        incident = request.input_data["incident"]
        decision = request.input_data["decision"]

        try:
            parsed = await self._llm.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=self._build_user_prompt(incident, decision, context),
            )
            return self._output_from_llm(parsed)
        except LLMClientError:
            self._logger.warning("tma_llm_failed_using_fallback")
            return self._fallback_memory(incident, decision)

    def _build_user_prompt(
        self, incident: dict[str, Any], decision: dict[str, Any], context: AgentContext | None
    ) -> str:
        venue_hint = f"Venue: {context.venue_id}\n" if context else ""
        return (
            f"{venue_hint}"
            f"Incident:\n{json.dumps(incident, indent=2)}\n\n"
            f"Consensus Decision:\n{json.dumps(decision, indent=2)}\n"
        )

    def _output_from_llm(self, parsed: dict[str, Any]) -> StructuredOutput:
        memory_summary = str(parsed.get("memory_summary", "")).strip()

        return StructuredOutput(
            data={
                "memory_summary": memory_summary or "Incident resolved.",
            },
            confidence=0.85,
            used_fallback=False,
            rationale="Memory summary generated by LLM.",
        )

    # -- Deterministic fallback --------------------------------------------

    def _fallback_memory(
        self, incident: dict[str, Any], decision: dict[str, Any]
    ) -> StructuredOutput:
        inc_type = incident.get("incident_type", "unknown")
        severity = incident.get("severity", "unknown")
        outcome = decision.get("outcome", "unknown")

        summary = (
            f"{severity.title()} {inc_type} incident resulted in consensus outcome: {outcome}."
        )

        return StructuredOutput(
            data={
                "memory_summary": summary,
            },
            confidence=0.3,
            used_fallback=True,
            rationale="LLM unavailable; memory summary generated via deterministic fallback.",
        )
