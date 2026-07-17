from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.events import EventSource
from app.db.models.incident import RAW_TEXT_MAX_LENGTH, IncidentSeverity, IncidentStatus


class IncidentBase(BaseModel):
    """Shared properties for all Incident schemas."""

    venue_id: uuid.UUID
    zone_id: uuid.UUID | None = None
    reported_by_user_id: uuid.UUID | None = None
    raw_text: str = Field(..., min_length=1, max_length=RAW_TEXT_MAX_LENGTH)
    language: str | None = Field(default=None, max_length=50)
    status: IncidentStatus = IncidentStatus.OPEN
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    source: EventSource = EventSource.LIVE


class IncidentCreate(IncidentBase):
    """Schema for creating a new Incident."""

    pass


class IncidentUpdate(BaseModel):
    """Schema for updating an existing Incident (patch)."""

    zone_id: uuid.UUID | None = None
    status: IncidentStatus | None = None
    severity: IncidentSeverity | None = None
    structured_summary: dict[str, Any] | None = None
    resolved_at: datetime | None = None


class IncidentResponse(IncidentBase):
    """Schema for returning an Incident to clients."""

    id: uuid.UUID
    structured_summary: dict[str, Any] | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
