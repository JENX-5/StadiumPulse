"""
Operational Consensus Agent (OCA).

Resolves disagreements between other agents (IAA, PIA, RCA) during a negotiation
session. It looks at all proposed actions, challenges, and rebuttals, and
determines the final accepted action (if any) that should be passed to the
Dispatch Service.

It implements the `ConsensusStrategy` protocol required by `NegotiationSession`.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentValidationError
from app.agents.types import (
    AgentContext,
    AgentRequest,
    ConsensusDecision,
    ConsensusOutcome,
    NegotiationMessage,
    NegotiationMessageType,
    StructuredOutput,
)
from app.core.exceptions import LLMClientError
from app.core.llm_client import LLMClient


SYSTEM_PROMPT = """You are the Operational Consensus component of a stadium operations platform.
Your job is to resolve disagreements between various specialized AI agents handling an incident.
You will receive a transcript of their negotiation (proposals, challenges, rebuttals, and votes).

Rules for Resolution:
1. If there is a clear consensus or one proposal is significantly more logical and well-supported, choose it.
2. If there are valid security or safety challenges that were not adequately rebutted, reject the flawed proposal.
3. If no proposal is safe or well-supported, declare "no_consensus".

Respond with a JSON object with exactly these keys:
- "outcome": either "accepted" or "no_consensus".
- "decision": the JSON object of the winning proposal (or null if no consensus).
- "rationale": a short string explaining why you made this choice.
"""


class OperationalConsensusAgent(BaseAgent):
    agent_id = "operational_consensus"
    name = "Operational Consensus Agent"
    description = (
        "Resolves multi-agent disagreements by determining the final consensus "
        "decision from a negotiation transcript."
    )
    system_prompt = SYSTEM_PROMPT
    supported_tasks: tuple[str, ...] = ("resolve_consensus",)

    max_retries = 1
    timeout_seconds = 20.0

    def __init__(self, *, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm = llm_client

    # -- Validation ---------------------------------------------------------

    def validate_input(self, request: AgentRequest) -> None:
        super().validate_input(request)
        messages = request.input_data.get("messages")
        
        if not isinstance(messages, list):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' requires 'messages' to be a list in input_data",
                details={"input_data_keys": list(request.input_data.keys())},
            )

    def validate_output(self, output: StructuredOutput) -> None:
        super().validate_output(output)
        data = output.data
        if data.get("outcome") not in (ConsensusOutcome.ACCEPTED.value, ConsensusOutcome.NO_CONSENSUS.value):
            raise AgentValidationError(
                f"Agent '{self.agent_id}' produced an invalid outcome: {data.get('outcome')}"
            )
        if not data.get("rationale"):
            raise AgentValidationError(f"Agent '{self.agent_id}' produced no rationale field")

    # -- Execution ------------------------------------------------------------

    async def _execute(
        self, request: AgentRequest, context: AgentContext | None
    ) -> StructuredOutput:
        messages = request.input_data["messages"]

        try:
            parsed = await self._llm.generate_json(
                system_prompt=self.system_prompt,
                user_prompt=self._build_user_prompt(messages, context),
            )
            return self._output_from_llm(parsed)
        except LLMClientError:
            self._logger.warning("oca_llm_failed_using_fallback")
            return self._fallback_resolve(messages)

    def _build_user_prompt(self, messages: list[dict[str, Any]], context: AgentContext | None) -> str:
        venue_hint = f"Venue: {context.venue_id}\n" if context else ""
        return (
            f"{venue_hint}"
            f"Negotiation Transcript:\n{json.dumps(messages, indent=2)}\n"
        )

    def _output_from_llm(self, parsed: dict[str, Any]) -> StructuredOutput:
        outcome_str = str(parsed.get("outcome", "")).strip().lower()
        if outcome_str == "accepted":
            outcome = ConsensusOutcome.ACCEPTED
        else:
            outcome = ConsensusOutcome.NO_CONSENSUS
            
        decision = parsed.get("decision")
        if not isinstance(decision, dict):
            decision = {}
            
        return StructuredOutput(
            data={
                "outcome": outcome.value,
                "decision": decision,
                "rationale": str(parsed.get("rationale", "")).strip() or "Resolved by LLM.",
            },
            confidence=0.85,
            used_fallback=False,
            rationale="Consensus resolved by LLM based on negotiation transcript.",
        )

    # -- Deterministic fallback --------------------------------------------

    def _fallback_resolve(self, messages: list[dict[str, Any]]) -> StructuredOutput:
        # Fallback to picking the proposal with the highest confidence
        proposals = [m for m in messages if m.get("phase") == NegotiationMessageType.PROPOSAL.value]
        
        if not proposals:
            return StructuredOutput(
                data={
                    "outcome": ConsensusOutcome.NO_CONSENSUS.value,
                    "decision": {},
                    "rationale": "No proposals were made.",
                },
                confidence=0.3,
                used_fallback=True,
                rationale="Fallback: no proposals.",
            )
            
        winner = max(proposals, key=lambda m: m.get("confidence", 0.0))
        
        return StructuredOutput(
            data={
                "outcome": ConsensusOutcome.ACCEPTED.value,
                "decision": winner.get("content", {}),
                "rationale": "Fallback strategy selected the highest confidence proposal.",
            },
            confidence=0.3,
            used_fallback=True,
            rationale="LLM unavailable; resolved via deterministic fallback.",
        )

    # -- ConsensusStrategy Protocol implementation ----------------------------

    async def resolve(self, incident_id: str, messages: list[NegotiationMessage]) -> ConsensusDecision:
        """Adapts the Agent interface to the ConsensusStrategy protocol."""
        
        # Serialize messages for the agent request
        serialized_messages = [
            {
                "turn_number": m.turn_number,
                "phase": m.phase.value,
                "agent_id": m.agent_id,
                "content": m.content,
                "confidence": m.confidence,
                "rationale": m.rationale,
            }
            for m in messages
        ]
        
        request = AgentRequest(
            task_type="resolve_consensus",
            input_data={"messages": serialized_messages},
        )
        
        # We don't have venue context here, but we can pass None.
        output = await self.execute(request, context=None)
        
        # Extract voting metrics
        votes = [m for m in messages if m.phase == NegotiationMessageType.VOTE]
        supporting = {v.agent_id for v in votes if v.content.get("supports") is True}
        dissenting = {v.agent_id for v in votes if v.content.get("supports") is False}
        
        winner_agent_id = "unknown"
        if output.data["outcome"] == ConsensusOutcome.ACCEPTED.value:
            # Try to attribute to the original proposer based on the decision content
            decision_content = output.data["decision"]
            for m in messages:
                if m.phase == NegotiationMessageType.PROPOSAL and m.content == decision_content:
                    winner_agent_id = m.agent_id
                    supporting.add(winner_agent_id)
                    break

        return ConsensusDecision(
            incident_id=incident_id,
            outcome=ConsensusOutcome(output.data["outcome"]),
            decision=output.data["decision"],
            supporting_agent_ids=sorted(supporting),
            dissenting_agent_ids=sorted(dissenting),
            confidence=output.confidence,
            rationale=output.data["rationale"],
            turn_count=len(messages),
        )
