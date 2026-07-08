"""
Incident: the central record produced by the Incident Analysis Agent from
raw (possibly multilingual) reporter text, and consumed by the Operational
Consensus Agent negotiation.

`raw_text` has an explicit max length (Recommended Fix #9 from the review:
bound prompt size sent to the Incident Analysis Agent, which is also a
direct LLM cost control). `structured_summary` holds the agent's JSON
extraction — kept schemaless (JSONB) at the DB layer since its shape is
owned and versioned by the Incident Analysis Agent module, not by the
database module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.events import EventSource
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.negotiation import Negotiation
    from app.db.models.resource_assignment import ResourceAssignment
    from app.db.models.venue import Venue
    from app.db.models.zone import Zone

# Enforced at the API layer too (Recommended Fix #9); this is defense-in-depth
# at the schema level so a bad row can never be written by any code path.
RAW_TEXT_MAX_LENGTH = 4000


class IncidentStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        # Phase 7 review: composite index on (venue_id, status, severity) —
        # this is the exact filter shape the Command Center's incident list
        # and GET /incidents pagination query use.
        Index("ix_incidents_venue_status_severity", "venue_id", "status", "severity"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
    )
    reported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    raw_text: Mapped[str] = mapped_column(String(RAW_TEXT_MAX_LENGTH), nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    structured_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus, name="incident_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=IncidentStatus.OPEN,
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        SAEnum(IncidentSeverity, name="incident_severity", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=IncidentSeverity.MEDIUM,
    )
    source: Mapped[EventSource] = mapped_column(
        SAEnum(EventSource, name="incident_source", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=EventSource.LIVE
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    venue: Mapped["Venue"] = relationship(back_populates="incidents")
    zone: Mapped["Zone | None"] = relationship(back_populates="incidents")
    negotiations: Mapped[list["Negotiation"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    resource_assignments: Mapped[list["ResourceAssignment"]] = relationship(
        back_populates="incident"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Incident {self.id} status={self.status} severity={self.severity}>"
