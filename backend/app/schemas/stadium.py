from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.db.models.resource import ResourceStatus, ResourceType


class VenueResponse(BaseModel):
    """Schema for a Venue."""

    id: uuid.UUID
    name: str
    timezone: str

    model_config = ConfigDict(from_attributes=True)


class ZoneResponse(BaseModel):
    """Schema for a Zone within a Venue."""

    id: uuid.UUID
    venue_id: uuid.UUID
    name: str
    capacity: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ResourceResponse(BaseModel):
    """Schema for a Resource (e.g., Medical Team, Volunteer)."""

    id: uuid.UUID
    venue_id: uuid.UUID
    current_zone_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    label: str
    resource_type: ResourceType
    status: ResourceStatus

    model_config = ConfigDict(from_attributes=True)
