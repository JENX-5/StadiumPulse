from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.events import EventSource


class IncidentCreatedPayload(BaseModel):
    """Payload for when an incident is created."""
    incident_id: str
    venue_id: str
    status: str
    severity: str
    raw_text: str


class IncidentUpdatedPayload(BaseModel):
    """Payload for when an incident is updated."""
    incident_id: str
    venue_id: str
    status: str | None = None
    severity: str | None = None


class EventResponse(BaseModel):
    """API response model for an Event."""
    event_id: str
    event_type: str
    source: EventSource
    occurred_at: str
    venue_id: str
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
