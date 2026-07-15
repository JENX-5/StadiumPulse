"""
Incident Analysis Agent (IAA).

Parses raw, unstructured incident-report text (radio call transcript,
steward's typed note, app submission) into the structured shape the rest
of the pipeline needs: type, severity, location, and a short factual
summary. This agent is a pure parser -- per the completion spec, it
"prepares structured input for the Orchestrator/OCA" and makes no
database writes and no dispatch decisions itself.

Follows the LLMClient's documented fallback contract (see
`core/llm_client.py`'s `generate_json` docstring): if the LLM call raises
`LLMClientError` after its one corrective retry, this agent does NOT
propagate that as an agent failure. It falls back to a deterministic
keyword-based classifier so incident intake degrades gracefully instead
of blocking on an LLM outage. The fallback's output is marked
`used_fallback=True` with a capped confidence so downstream consumers
(OCA, dispatch) can weight it accordingly.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentValidationError
from app.agents.types import AgentContext, AgentRequest, StructuredOutput
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient


class IncidentType(StrEnum):
    MEDICAL = "medical"
    SECURITY = "security"
    FIRE = "fire"
    CROWD_CRUSH = "crowd_crush"
    WEATHER = "weather"
    TECHNICAL = "technical"
    OTHER = "other"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_VALID_TYPES = {t.value for t in IncidentType}
_VALID_SEVERITIES = {s.value for s in IncidentSeverity}

SYSTEM_PROMPT = """You are the Incident Analysis component of a stadium \
operations platform. You convert a single raw incident report -- a radio \
transcript, steward note, or app submission -- into structured data.

Extract only what the text actually supports; never invent a location or \
severity that isn't implied by the text. If something is not mentioned, \
use "unknown" for location or the lowest defensible severity.

Respond with a JSON object with exactly these keys:
- "incident_type": one of ["medical", "security", "fire", "crowd_crush", \
"weather", "technical", "other"]
- "severity": one of ["low", "medium", "high", "critical"]
- "location": short free-text location/zone description, or "unknown"
- "summary": one factual sentence summarizing what was reported
- "keywords": a list of up to 5 short keywords/entities extracted from the text
"""

# Deterministic fallback classifier -- deliberately crude (keyword match).
# Used ONLY when the LLM call fails after its corrective retry, so an LLM
# outage degrades incident intake to "coarse but available" instead of
# blocking it. Keep this simple; if it needs to get smarter than keyword
# matching, that's a sign the real fix is LLM reliability, not this path.
_TYPE_KEYWORDS: dict[IncidentType, tuple[str, ...]] = {
    IncidentType.FIRE: ("fire", "smoke", "burning", "flame"),
    IncidentType.MEDICAL: ("injur", "collapse", "unconscious", "medical", "bleeding", "seizure"),
    IncidentType.CROWD_CRUSH: ("crush", "surge", "overcrowd", "stampede", "trampl"),
    IncidentType.SECURITY: ("fight", "weapon", "assault", "threat", "intruder", "theft"),
    IncidentType.WEATHER: ("lightning", "storm", "flood", "wind", "hail"),
    IncidentType.TECHNICAL: ("power", "outage", "failure", "malfunction", "system down"),
}
_SEVERITY_KEYWORDS: dict[IncidentSeverity, tuple[str, ...]] = {
    IncidentSeverity.CRITICAL: ("critical", "life-threatening", "mass casualty", "unresponsive"),
    IncidentSeverity.HIGH: ("severe", "urgent", "serious", "multiple"),
    IncidentSeverity.MEDIUM: ("moderate", "injured", "hurt"),
}
_LOCATION_PATTERN = re.compile(
    r"\b(gate|section|zone|stand|concourse|block)\s*[a-z0-9\-]+", re.IGNORECASE
)


class IncidentAnalysisAgent(BaseAgent):
    agent_id = "incident_analysis"
    name = "Incident Analysis Agent"
    description = (
        "Parses raw incident-report text into structured incident data "
        "(type, severity, location) for the orchestrator and OCA."
    )
    system_prompt = SYSTEM_PROMPT
    supported_tasks: tuple[str, ...] = ("incident_analysis",)

    max_retries = 1
    timeout_seconds = 20.0

    def __init__(self, *, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm = llm_client

    # -- Validation ---------------------------------------------------------

    def validate_input(self, request: AgentRequest) -> None:
        super().validate_input(request)
        raw_text = request.input_data.get("raw_text")
        if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires a non-empty 'raw_text' string in input_data",
                details={"input_data_keys": list(request.input_data.keys())},
            )

    def validate_output(self, output: StructuredOutput) -> None:
        super().validate_output(output)
        data = output.data
        if data.get("incident_type") not in _VALID_TYPES:
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid incident_type: "
                f"{data.get('incident_type')!r}"
            )
        if data.get("severity") not in _VALID_SEVERITIES:
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid severity: {data.get('severity')!r}"
            )
        if not data.get("location"):
            raise AgentValidationError(f"Agent '{self.agent_id}' produced no location field")
        if not data.get("summary"):
            raise AgentValidationError(f"Agent '{self.agent_id}' produced no summary field")

    # -- Execution ------------------------------------------------------------

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        raw_text = request.input_data["raw_text"].strip()

        try:
            parsed = await self._llm.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=self._build_user_prompt(raw_text, context),
            )
            return self._output_from_llm(parsed)
        except LLMClientError:
            self._logger.warning("iaa_llm_failed_using_fallback")
            return self._fallback_classify(raw_text)

    def _build_user_prompt(self, raw_text: str, context: AgentContext | None) -> str:
        venue_hint = f"Venue ID: {context.venue_id}\n" if context and context.venue_id else ""
        return f'{venue_hint}Incident report:\n<incident_data>\n{raw_text}\n</incident_data>'

    def _output_from_llm(self, parsed: dict[str, Any]) -> StructuredOutput:
        incident_type = str(parsed.get("incident_type", "")).strip().lower()
        severity = str(parsed.get("severity", "")).strip().lower()
        location = str(parsed.get("location", "")).strip() or "unknown"
        summary = str(parsed.get("summary", "")).strip()
        keywords = parsed.get("keywords")
        if not isinstance(keywords, list):
            keywords = []

        # The LLM occasionally drifts off the enum despite the prompt
        # constraint -- coerce to a safe default rather than raising, since
        # `validate_output` already guarantees this method's return value
        # is enum-valid before it ever reaches the caller.
        if incident_type not in _VALID_TYPES:
            incident_type = IncidentType.OTHER.value
        if severity not in _VALID_SEVERITIES:
            severity = IncidentSeverity.MEDIUM.value

        return StructuredOutput(
            data={
                "incident_type": incident_type,
                "severity": severity,
                "location": location,
                "summary": summary or "No summary extracted.",
                "keywords": [str(k) for k in keywords[:5]],
            },
            confidence=0.85,
            used_fallback=False,
            rationale="Parsed by LLM from raw incident report text.",
        )

    # -- Deterministic fallback --------------------------------------------

    def _fallback_classify(self, raw_text: str) -> StructuredOutput:
        lowered = raw_text.lower()

        incident_type = IncidentType.OTHER
        for candidate, keywords in _TYPE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                incident_type = candidate
                break

        severity = IncidentSeverity.LOW
        for candidate, keywords in _SEVERITY_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                severity = candidate
                break

        location_match = _LOCATION_PATTERN.search(raw_text)
        location = location_match.group(0) if location_match else "unknown"
        summary = (raw_text.strip().splitlines() or [""])[0][:200]

        return StructuredOutput(
            data={
                "incident_type": incident_type.value,
                "severity": severity.value,
                "location": location,
                "summary": summary,
                "keywords": [],
            },
            confidence=0.3,
            used_fallback=True,
            rationale="LLM unavailable; classified via deterministic keyword fallback.",
        )
