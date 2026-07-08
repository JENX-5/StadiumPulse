"""Zone: a spatial subdivision of a venue (e.g. 'North Concourse', 'Section 114').

This is the unit the Risk Heatmap renders and the Risk Scoring Function
computes over — every incident and every risk score is anchored to a zone.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.incident import Incident
    from app.db.models.resource import Resource
    from app.db.models.risk_score import RiskScore
    from app.db.models.venue import Venue


class Zone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "zones"

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    venue: Mapped["Venue"] = relationship(back_populates="zones")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="zone")
    risk_scores: Mapped[list["RiskScore"]] = relationship(back_populates="zone")
    resources: Mapped[list["Resource"]] = relationship(back_populates="current_zone")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Zone {self.name}>"
