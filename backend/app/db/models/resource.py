"""
Resource: the roster entry (medical, security, cleaning, volunteer, etc.)
that the Resource Coordination Agent ranks and Dispatch Service assigns.

`status` + `current_zone_id` together are exactly what the SQL pre-filter
(Critical Fix #2) queries on before the LLM ever sees a shortlist —
`SELECT * FROM resources WHERE venue_id = :v AND status = 'available' ...`
happens here, entirely outside the agent.
"""

from __future__ import annotations

import uuid
import enum
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, enum.Enum):
        pass
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.resource_assignment import ResourceAssignment
    from app.db.models.user import User
    from app.db.models.venue import Venue
    from app.db.models.zone import Zone


class ResourceType(StrEnum):
    MEDICAL = "medical"
    SECURITY = "security"
    CLEANING = "cleaning"
    VOLUNTEER = "volunteer"
    MAINTENANCE = "maintenance"


class ResourceStatus(StrEnum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    BUSY = "busy"
    OFFLINE = "offline"


class Resource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resources"

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False
    )
    current_zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
    )
    # Nullable: not every resource (e.g. a fixed medical station) maps to a
    # logged-in user; volunteers and staff do.
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )

    label: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(
        SAEnum(ResourceType, name="resource_type", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    status: Mapped[ResourceStatus] = mapped_column(
        SAEnum(ResourceStatus, name="resource_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ResourceStatus.AVAILABLE,
    )

    venue: Mapped["Venue"] = relationship(back_populates="resources")
    current_zone: Mapped["Zone | None"] = relationship(back_populates="resources")
    assigned_user: Mapped["User | None"] = relationship(back_populates="resource_profile")
    assignments: Mapped[list["ResourceAssignment"]] = relationship(back_populates="resource")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resource {self.label} ({self.resource_type}, {self.status})>"
