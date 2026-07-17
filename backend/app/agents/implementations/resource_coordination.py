"""
Resource Coordination Agent (RCA).

Takes a structured incident and a pre-filtered list of available resources
from the venue, and uses the LLM to output a ranked shortlist of resources
best suited to handle the incident based on proximity, type, and severity.

As per ADR-0002, the RCA is a pure reasoning function. It does NOT write
to the `resource_assignments` database table and does NOT trigger notifications.
It merely returns a ranked candidate list that the Dispatch Service will act on.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentValidationError
from app.agents.types import AgentContext, AgentRequest, StructuredOutput
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient

SYSTEM_PROMPT = """You are the Resource Coordination component of a stadium operations platform.
You are given a structured incident report and a list of currently available resources.
Your job is to rank the available resources from most suitable to least suitable for handling this incident.

Consider the following rules when ranking:
1. Type match: Medical incidents require medical resources. Security incidents require security resources.
2. Severity match: Critical incidents require the most capable or multiple resources.
3. If no perfectly matching resource is available, suggest the next best alternatives (e.g., security for crowd control during a medical event).

Respond with a JSON object with exactly these keys:
- "ranked_resource_ids": a list of string resource IDs ordered from most suitable to least suitable.
- "rationale": a short string explaining your top choices.
"""


class ResourceCoordinationAgent(BaseAgent):
    agent_id = "resource_coordination"
    name = "Resource Coordination Agent"
    description = (
        "Proposes a ranked candidate list of resources for an incident based on "
        "type, severity, and availability. Does not perform dispatch writes."
    )
    system_prompt = SYSTEM_PROMPT
    supported_tasks: tuple[str, ...] = ("rank_resources",)

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
        incident = request.input_data.get("incident")
        available_resources = request.input_data.get("available_resources")

        if not incident or not isinstance(incident, dict):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires a valid 'incident' dictionary in input_data",
                details={"input_data_keys": list(request.input_data.keys())},
            )
        if not isinstance(available_resources, list):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'available_resources' to be a list in input_data"
            )

    def validate_output(self, output: StructuredOutput) -> None:
        super().validate_output(output)
        data = output.data
        if "ranked_resource_ids" not in data or not isinstance(data["ranked_resource_ids"], list):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid or missing 'ranked_resource_ids' list"
            )
        if not data.get("rationale"):
            raise AgentValidationError(f"Agent '{self.agent_id}' produced no rationale field")

    # -- Execution ------------------------------------------------------------

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        incident = request.input_data["incident"]
        available_resources = request.input_data["available_resources"]

        try:
            parsed = await self._llm.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=self._build_user_prompt(incident, available_resources, context),
            )
            return self._output_from_llm(parsed)
        except LLMClientError:
            self._logger.warning("rca_llm_failed_using_fallback")
            return self._fallback_rank(incident, available_resources)

    def _build_user_prompt(
        self,
        incident: dict[str, Any],
        available_resources: list[dict[str, Any]],
        context: AgentContext | None,
    ) -> str:
        venue_hint = f"Venue: {context.venue_id}\n" if context else ""
        return (
            f"{venue_hint}"
            f"Incident:\n{json.dumps(incident, indent=2)}\n\n"
            f"Available Resources:\n{json.dumps(available_resources, indent=2)}\n"
        )

    def _output_from_llm(self, parsed: dict[str, Any]) -> StructuredOutput:
        ranked_resource_ids = parsed.get("ranked_resource_ids", [])
        if not isinstance(ranked_resource_ids, list):
            ranked_resource_ids = []

        return StructuredOutput(
            data={
                "ranked_resource_ids": [str(rid) for rid in ranked_resource_ids],
                "rationale": str(parsed.get("rationale", "Generated by LLM.")).strip(),
            },
            confidence=0.85,
            used_fallback=False,
            rationale="Ranked by LLM based on incident details and available resources.",
        )

    # -- Deterministic fallback --------------------------------------------

    def _fallback_rank(
        self, incident: dict[str, Any], available_resources: list[dict[str, Any]]
    ) -> StructuredOutput:
        # A very basic fallback that ranks matching types first
        incident_type = incident.get("incident_type", "").lower()

        def score_resource(r: dict[str, Any]) -> int:
            score = 0
            # 1. Exact type match
            if r.get("resource_type", "").lower() == incident_type:
                score += 10
            # 2. Could add zone proximity here in the future if location data is passed
            return score

        ranked = sorted(available_resources, key=score_resource, reverse=True)
        ranked_ids = [str(r.get("id")) for r in ranked if r.get("id")]

        return StructuredOutput(
            data={
                "ranked_resource_ids": ranked_ids,
                "rationale": "Fallback ranking based on naive type matching.",
            },
            confidence=0.3,
            used_fallback=True,
            rationale="LLM unavailable; ranked via deterministic fallback.",
        )
