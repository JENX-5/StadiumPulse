"""
Negotiation: one turn in the Operational Consensus Agent's negotiation
state machine (Proposal -> Challenge -> Rebuttal -> Resolution).

Persisting every turn as its own row — rather than one blob per incident —
is what makes the Explainability Drawer possible: the frontend renders this
table's rows in order to reconstruct the full negotiation transcript for a
given incident, and the inline Resolution-card rationale (Phase 3 fix) is
just the latest row where phase = 'resolution'.
"""

from __future__ import annotations

import uuid
import enum
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, enum.Enum):
        pass
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.incident import Incident


class NegotiationPhase(StrEnum):
    PROPOSAL = "proposal"
    CHALLENGE = "challenge"
    REBUTTAL = "rebuttal"
    RESOLUTION = "resolution"


class Negotiation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "negotiations"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    phase: Mapped[NegotiationPhase] = mapped_column(
        SAEnum(NegotiationPhase, name="negotiation_phase", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    # Monotonic per-incident turn counter so the frontend can render the
    # transcript in order without relying on timestamp precision alone.
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # The proposing/challenging agent's identifier, e.g. "predictive_intelligence",
    # "resource_coordination", "incident_analysis". Free-text rather than an enum
    # so a new agent can participate without a schema migration.
    agent_name: Mapped[str] = mapped_column(nullable=False)

    # Full structured content for this turn (the agent's JSON output for this
    # phase) plus a short human-readable rationale surfaced inline on the
    # Resolution card (Phase 3 UX fix) without needing the full JSON.
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str | None] = mapped_column(nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="negotiations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Negotiation incident={self.incident_id} phase={self.phase} turn={self.turn_number}>"
