"""
Predictive Intelligence Agent (PIA).

Triggered when the deterministic risk score (calculated by RiskScoringService)
crosses a critical threshold. Uses the LLM to generate a human-readable
narrative risk analysis explaining the score, based on the contributing factors.

As per ADR-0001, the LLM is invoked ONLY to generate the narrative, decoupling
the expensive LLM call from the hot read path of the polling risk heatmap.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentValidationError
from app.agents.types import AgentContext, AgentRequest, StructuredOutput
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient

SYSTEM_PROMPT = """You are the Predictive Intelligence component of a stadium operations platform.
A specific zone in the venue has just crossed a critical risk score threshold.
You will be provided with the zone's risk score and the breakdown of contributing factors
(e.g., crowd density, crowd velocity, noise level, incident proximity, historical pattern match).

Your job is to generate a concise, human-readable narrative explaining why this zone is high risk,
what the primary contributing factors are, and any immediate operational concerns.

Respond with a JSON object with exactly this key:
- "narrative": a 1-2 sentence text summarizing the risk situation for operations staff.
"""


class PredictiveIntelligenceAgent(BaseAgent):
    agent_id = "predictive_intelligence"
    name = "Predictive Intelligence Agent"
    description = (
        "Generates a human-readable narrative risk analysis when a zone's "
        "deterministic risk score crosses a critical threshold."
    )
    system_prompt = SYSTEM_PROMPT
    supported_tasks: tuple[str, ...] = ("generate_narrative",)

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

        if "zone_id" not in data:
            raise AgentValidationError(f"Agent '{self.agent_id}' requires 'zone_id' in input_data")
        if "risk_score" not in data:
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'risk_score' in input_data"
            )
        if "contributing_factors" not in data or not isinstance(data["contributing_factors"], dict):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'contributing_factors' dictionary in input_data"
            )

    def validate_output(self, output: StructuredOutput) -> None:
        super().validate_output(output)
        data = output.data
        if not data.get("narrative") or not isinstance(data["narrative"], str):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid or missing 'narrative' string"
            )

    # -- Execution ------------------------------------------------------------

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        zone_id = request.input_data["zone_id"]
        risk_score = request.input_data["risk_score"]
        contributing_factors = request.input_data["contributing_factors"]

        try:
            parsed = await self._llm.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=self._build_user_prompt(
                    zone_id, risk_score, contributing_factors, context
                ),
            )
            return self._output_from_llm(parsed)
        except LLMClientError:
            self._logger.warning("pia_llm_failed_using_fallback")
            return self._fallback_narrative(zone_id, risk_score, contributing_factors)

    def _build_user_prompt(
        self,
        zone_id: str,
        risk_score: float,
        contributing_factors: dict[str, float],
        context: AgentContext | None,
    ) -> str:
        venue_hint = f"Venue: {context.venue_id}\n" if context else ""
        return (
            f"{venue_hint}"
            f"Zone ID: {zone_id}\n"
            f"Risk Score: {risk_score}\n"
            f"Contributing Factors:\n{json.dumps(contributing_factors, indent=2)}\n"
        )

    def _output_from_llm(self, parsed: dict[str, Any]) -> StructuredOutput:
        narrative = str(parsed.get("narrative", "")).strip()

        return StructuredOutput(
            data={
                "narrative": narrative or "High risk detected in zone.",
            },
            confidence=0.85,
            used_fallback=False,
            rationale="Narrative generated by LLM based on risk score and factors.",
        )

    # -- Deterministic fallback --------------------------------------------

    def _fallback_narrative(
        self, zone_id: str, risk_score: float, contributing_factors: dict[str, float]
    ) -> StructuredOutput:

        # Identify the highest contributing factor
        if contributing_factors:
            primary_factor = max(contributing_factors.items(), key=lambda x: x[1])
            factor_name = primary_factor[0].replace("_", " ").title()
            narrative = f"High risk score of {risk_score} detected. Primary contributing factor: {factor_name}."
        else:
            narrative = f"High risk score of {risk_score} detected in zone."

        return StructuredOutput(
            data={
                "narrative": narrative,
            },
            confidence=0.3,
            used_fallback=True,
            rationale="LLM unavailable; narrative generated via deterministic fallback.",
        )
