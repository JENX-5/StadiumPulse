"""
Common types shared by every agent, the orchestrator, and the negotiation
engine.

These are Pydantic models (not plain dataclasses) deliberately: every one
of them either crosses a serialization boundary (Redis event payloads,
API responses, JSONB columns) or needs the schema validation that
`StructuredOutput`/`AgentResponse` rely on, so getting `.model_dump()` /
`.model_validate()` for free everywhere is worth the small overhead vs.
`@dataclass`.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

try:
    from enum import StrEnum
except ImportError:

    class StrEnum(str, enum.Enum):
        pass


from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class NegotiationMessageType(StrEnum):
    """Mirrors `app.db.models.negotiation.NegotiationPhase` (ADR-0002 transcript
    model) — kept as a separate enum here rather than importing the ORM enum
    directly, so the in-memory negotiation engine has no hard dependency on
    the database layer and stays unit-testable without a DB session."""

    PROPOSAL = "proposal"
    CHALLENGE = "challenge"
    REBUTTAL = "rebuttal"
    VOTE = "vote"
    RESOLUTION = "resolution"


class ConsensusOutcome(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NO_CONSENSUS = "no_consensus"


class StructuredOutput(BaseModel):
    """The normalized shape every agent's `_execute` must return.

    `data` holds the agent-specific payload (validated separately by that
    agent's own schema); this envelope only standardizes the parts every
    caller needs regardless of which agent produced it: how confident the
    agent is, and whether it fell back to a rule-based path because the LLM
    call failed (Critical Fix #4's documented fallback contract).
    """

    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    used_fallback: bool = False
    rationale: str | None = None

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, value))


class AgentContext(BaseModel):
    """Read-mostly context an agent needs to reason, assembled by the
    Shared Context Manager before each execution."""

    venue_id: str
    incident_id: str | None = None
    current_incident: dict[str, Any] | None = None
    venue_state: dict[str, Any] = Field(default_factory=dict)
    risk_info: dict[str, Any] = Field(default_factory=dict)
    historical_context: list[dict[str, Any]] = Field(default_factory=list)
    shared_variables: dict[str, Any] = Field(default_factory=dict)


class AgentMemory(BaseModel):
    """A single retrieved memory item handed to an agent as extra context.

    Deliberately generic (`content` + `metadata`) — the Tournament Memory
    Agent (future module) is one *source* of these, not the only one; any
    `MemoryProvider` implementation can produce `AgentMemory` items.
    """

    memory_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)


class AgentRequest(BaseModel):
    """A single unit of work handed to an agent by the orchestrator."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    context: AgentContext | None = None
    memories: list[AgentMemory] = Field(default_factory=list)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResponse(BaseModel):
    """What `BaseAgent.execute()` returns to the orchestrator."""

    request_id: str
    agent_id: str
    status: AgentTaskStatus
    output: StructuredOutput | None = None
    error_message: str | None = None
    duration_ms: float | None = None
    attempts: int = 1
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskResult(BaseModel):
    """One step's outcome inside an orchestrated workflow — a thin wrapper
    around `AgentResponse` that also records which workflow step produced
    it, so the orchestrator's overall result can be reconstructed in order."""

    step_index: int
    agent_id: str
    task_type: str
    response: AgentResponse | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.response is not None and self.response.status == AgentTaskStatus.SUCCEEDED


class NegotiationMessage(BaseModel):
    """One turn in a negotiation session (in-memory representation).

    Persisted to the `negotiations` table 1:1 by whichever caller owns
    that responsibility (Operational Consensus Agent, future module) —
    this framework only manages the in-memory session and history.
    """

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    turn_number: int
    phase: NegotiationMessageType
    agent_id: str
    content: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusDecision(BaseModel):
    """The final output of a negotiation session."""

    incident_id: str
    outcome: ConsensusOutcome
    decision: dict[str, Any] = Field(default_factory=dict)
    supporting_agent_ids: list[str] = Field(default_factory=list)
    dissenting_agent_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = None
    turn_count: int = 0
