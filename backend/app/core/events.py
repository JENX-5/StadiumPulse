"""
Shared event contract for the Event Bus (Redis pub/sub).

Every event published anywhere in the system — simulation traffic or real
venue traffic — must be an `Event`. The `source` field (Critical Fix: event
provenance tagging) exists specifically so demo/simulation data can never be
mistaken for live production data downstream, at zero runtime cost.

This module defines the envelope and channel names only. Per-domain payload
schemas (IncidentCreated, RiskScoreUpdated, ResourceAssigned, etc.) are
introduced in their owning modules and imported here as they land — this
file is intentionally minimal at the foundation stage.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventSource(StrEnum):
    SIMULATION = "simulation"
    LIVE = "live"


class EventChannel(StrEnum):
    """Redis pub/sub channel names. Centralized so no module hardcodes a string."""

    INCIDENTS = "channel:incidents"
    RISK_SCORES = "channel:risk_scores"
    RESOURCE_ASSIGNMENTS = "channel:resource_assignments"
    TOURNAMENT_MEMORY = "channel:tournament_memory"


class Event(BaseModel):
    """Envelope wrapping every message published on the Event Bus.

    `payload` is intentionally `dict[str, Any]` at this stage — typed
    per-event payload models are added alongside the module that owns them
    (e.g. Incident Analysis Agent introduces `IncidentCreatedPayload`) and
    validated by the publisher before `payload.model_dump()` is placed here.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    source: Literal[EventSource.SIMULATION, EventSource.LIVE]
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    venue_id: str
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        return cls.model_validate(json.loads(raw))
