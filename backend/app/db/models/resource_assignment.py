"""
ResourceAssignment: the ONLY table Dispatch Service is allowed to write to
(ADR-0002 / Critical Fix #3). The Resource Coordination Agent's ranked
proposals live in `Negotiation` rows (content JSONB, phase='proposal') —
they never reach this table directly. Only Dispatch Service, after reading
a resolved negotiation, inserts here.

`assigned_by` is a free-text system marker rather than a user_id because
dispatch can be triggered automatically (no human in the loop) as well as
manually overridden by an admin — both cases need to be representable.
"""

from __future__ import annotations

import uuid
from datetime import datetime
import enum
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, enum.Enum):
        pass
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.incident import Incident
    from app.db.models.resource import Resource


class AssignmentStatus(StrEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    EN_ROUTE = "en_route"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ResourceAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resource_assignments"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, name="assignment_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AssignmentStatus.PENDING,
    )
    # e.g. "dispatch_service" (automatic) or "user:<uuid>" (manual override).
    assigned_by: Mapped[str] = mapped_column(String(200), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="resource_assignments")
    resource: Mapped["Resource"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResourceAssignment incident={self.incident_id} resource={self.resource_id}>"
