"""
Negotiation framework.

Manages one negotiation session's turn-by-turn state machine (proposal ->
challenge -> rebuttal -> vote -> resolution) and produces a
`ConsensusDecision`. Per Module 3's scope, the actual *strategy* for
resolving disagreement (how the Operational Consensus Agent should weigh
competing proposals) is a future module's business logic — the
`ConsensusStrategy` protocol here is the seam that logic plugs into.
`HighestConfidenceStrategy` is included only as a working default so this
framework is exercisable/testable end-to-end today; it is explicitly a
placeholder, not the product's real negotiation strategy.

Session state is in-memory and transient. Persisting each `NegotiationMessage`
to the `negotiations` table (Module 2, ADR: Explainability Drawer) is the
caller's responsibility once a real agent produces these messages.
"""

from __future__ import annotations

from typing import Protocol

import structlog

from app.agents.exceptions import NegotiationError
from app.agents.types import (
    ConsensusDecision,
    ConsensusOutcome,
    NegotiationMessage,
    NegotiationMessageType,
)

logger = structlog.get_logger(__name__)

# Valid phase transitions per turn — enforced so a caller can't, say, record
# a "resolution" before any proposal exists. Multiple proposals/challenges/
# rebuttals/votes in a row are allowed (multi-agent negotiation), but a
# session can only be resolved once.
_ALLOWED_NEXT_PHASES: dict[NegotiationMessageType | None, set[NegotiationMessageType]] = {
    None: {NegotiationMessageType.PROPOSAL, NegotiationMessageType.RESOLUTION},
    NegotiationMessageType.PROPOSAL: {
        NegotiationMessageType.PROPOSAL,
        NegotiationMessageType.CHALLENGE,
        NegotiationMessageType.VOTE,
        NegotiationMessageType.RESOLUTION,
    },
    NegotiationMessageType.CHALLENGE: {
        NegotiationMessageType.REBUTTAL,
        NegotiationMessageType.CHALLENGE,
        NegotiationMessageType.VOTE,
        NegotiationMessageType.RESOLUTION,
    },
    NegotiationMessageType.REBUTTAL: {
        NegotiationMessageType.CHALLENGE,
        NegotiationMessageType.VOTE,
        NegotiationMessageType.PROPOSAL,
        NegotiationMessageType.RESOLUTION,
    },
    NegotiationMessageType.VOTE: {
        NegotiationMessageType.VOTE,
        NegotiationMessageType.RESOLUTION,
    },
    NegotiationMessageType.RESOLUTION: set(),  # terminal
}


class ConsensusStrategy(Protocol):
    """Pluggable strategy for turning a session's message history into a
    `ConsensusDecision`. Concrete strategies (majority vote with veto
    rules, weighted-by-agent-track-record, etc.) belong to future modules."""

    async def resolve(
        self, incident_id: str, messages: list[NegotiationMessage]
    ) -> ConsensusDecision: ...


class HighestConfidenceStrategy:
    """Placeholder default strategy: picks the highest-confidence proposal
    among all PROPOSAL messages, "voters" being any VOTE message that
    references the same agent_id count as support/dissent.

    This is intentionally simplistic — real consensus logic (handling
    genuine disagreement, tie-breaks, minority-report cases) is explicitly
    out of scope for Module 3.
    """

    async def resolve(self, incident_id: str, messages: list[NegotiationMessage]) -> ConsensusDecision:
        proposals = [m for m in messages if m.phase == NegotiationMessageType.PROPOSAL]
        votes = [m for m in messages if m.phase == NegotiationMessageType.VOTE]

        if not proposals:
            return ConsensusDecision(
                incident_id=incident_id,
                outcome=ConsensusOutcome.NO_CONSENSUS,
                rationale="No proposals were made.",
                turn_count=len(messages),
            )

        winner = max(proposals, key=lambda m: m.confidence)
        supporting = {v.agent_id for v in votes if v.content.get("supports") is True}
        dissenting = {v.agent_id for v in votes if v.content.get("supports") is False}

        return ConsensusDecision(
            incident_id=incident_id,
            outcome=ConsensusOutcome.ACCEPTED,
            decision=winner.content,
            supporting_agent_ids=sorted(supporting | {winner.agent_id}),
            dissenting_agent_ids=sorted(dissenting),
            confidence=winner.confidence,
            rationale=winner.rationale
            or "Highest-confidence proposal selected (placeholder strategy).",
            turn_count=len(messages),
        )


class NegotiationSession:
    """One incident's negotiation transcript plus the machinery to append
    turns and resolve them into a decision."""

    def __init__(self, incident_id: str, *, strategy: ConsensusStrategy | None = None) -> None:
        self.incident_id = incident_id
        self._messages: list[NegotiationMessage] = []
        self._strategy = strategy or HighestConfidenceStrategy()
        self._resolved = False

    @property
    def history(self) -> list[NegotiationMessage]:
        return list(self._messages)

    @property
    def turn_count(self) -> int:
        return len(self._messages)

    def _last_phase(self) -> NegotiationMessageType | None:
        return self._messages[-1].phase if self._messages else None

    def _append(
        self,
        phase: NegotiationMessageType,
        *,
        agent_id: str,
        content: dict,
        confidence: float = 0.5,
        rationale: str | None = None,
    ) -> NegotiationMessage:
        if self._resolved:
            raise NegotiationError(
                f"Negotiation for incident '{self.incident_id}' is already resolved; no further turns allowed."
            )
        last_phase = self._last_phase()
        allowed = _ALLOWED_NEXT_PHASES[last_phase]
        if phase not in allowed:
            raise NegotiationError(
                f"Cannot record phase '{phase}' after '{last_phase}' "
                f"for incident '{self.incident_id}' (allowed next: {sorted(allowed)})"
            )
        message = NegotiationMessage(
            incident_id=self.incident_id,
            turn_number=len(self._messages) + 1,
            phase=phase,
            agent_id=agent_id,
            content=content,
            confidence=confidence,
            rationale=rationale,
        )
        self._messages.append(message)
        logger.info(
            "negotiation_turn_recorded",
            incident_id=self.incident_id,
            phase=phase,
            agent_id=agent_id,
            turn_number=message.turn_number,
        )
        if phase == NegotiationMessageType.RESOLUTION:
            self._resolved = True
        return message

    def propose(
        self, *, agent_id: str, content: dict, confidence: float = 0.5, rationale: str | None = None
    ) -> NegotiationMessage:
        return self._append(
            NegotiationMessageType.PROPOSAL,
            agent_id=agent_id,
            content=content,
            confidence=confidence,
            rationale=rationale,
        )

    def challenge(
        self, *, agent_id: str, content: dict, confidence: float = 0.5, rationale: str | None = None
    ) -> NegotiationMessage:
        return self._append(
            NegotiationMessageType.CHALLENGE,
            agent_id=agent_id,
            content=content,
            confidence=confidence,
            rationale=rationale,
        )

    def rebut(
        self, *, agent_id: str, content: dict, confidence: float = 0.5, rationale: str | None = None
    ) -> NegotiationMessage:
        return self._append(
            NegotiationMessageType.REBUTTAL,
            agent_id=agent_id,
            content=content,
            confidence=confidence,
            rationale=rationale,
        )

    def vote(
        self,
        *,
        agent_id: str,
        supports: bool,
        confidence: float = 0.5,
        rationale: str | None = None,
    ) -> NegotiationMessage:
        return self._append(
            NegotiationMessageType.VOTE,
            agent_id=agent_id,
            content={"supports": supports},
            confidence=confidence,
            rationale=rationale,
        )

    async def resolve(self) -> ConsensusDecision:
        """Run the configured `ConsensusStrategy` and record the resulting
        decision as the session's terminal RESOLUTION turn."""
        decision = await self._strategy.resolve(self.incident_id, self.history)
        self._append(
            NegotiationMessageType.RESOLUTION,
            agent_id="negotiation_engine",
            content=decision.model_dump(),
            confidence=decision.confidence,
            rationale=decision.rationale,
        )
        return decision


class NegotiationEngine:
    """Owns all active/completed negotiation sessions, keyed by incident_id."""

    def __init__(self, *, strategy: ConsensusStrategy | None = None) -> None:
        self._strategy = strategy or HighestConfidenceStrategy()
        self._sessions: dict[str, NegotiationSession] = {}

    def start_session(self, incident_id: str) -> NegotiationSession:
        if incident_id in self._sessions:
            raise NegotiationError(
                f"A negotiation session already exists for incident '{incident_id}'"
            )
        session = NegotiationSession(incident_id, strategy=self._strategy)
        self._sessions[incident_id] = session
        return session

    def get_session(self, incident_id: str) -> NegotiationSession:
        session = self._sessions.get(incident_id)
        if session is None:
            raise NegotiationError(f"No negotiation session found for incident '{incident_id}'")
        return session

    def get_or_start(self, incident_id: str) -> NegotiationSession:
        return self._sessions.get(incident_id) or self.start_session(incident_id)

    def end_session(self, incident_id: str) -> None:
        self._sessions.pop(incident_id, None)
