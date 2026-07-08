"""
RiskScore: time-series history of the deterministic scorer's output per
zone (ADR-0001).

Phase 7 review finding: this table is read very frequently by the Risk
Heatmap (every zone, every few seconds). Per that finding, the **current**
score per zone is cached in Redis by the scorer service and this table is
write-through, history-only — the heatmap should poll Redis, not this
table. This model exists for the audit trail / trend charts, not the
hot read path.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.zone import Zone


class RiskScoreSource(StrEnum):
    # Written every tick by the deterministic scorer (ADR-0001).
    DETERMINISTIC = "deterministic"
    # Written when the LLM narrative step also updates the record with
    # human-readable context, on threshold-cross only.
    LLM_NARRATIVE = "llm_narrative"


class RiskScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        # The hot query is "give me this zone's history in time order" —
        # this index serves that directly. computed_at is stored separately
        # from created_at in case a backfill or replay ever writes historical
        # scores out of insertion order.
        Index("ix_risk_scores_zone_computed_at", "zone_id", "computed_at"),
    )

    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[RiskScoreSource] = mapped_column(
        SAEnum(RiskScoreSource, name="risk_score_source", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    # Weighted-function inputs (density, velocity, historical-pattern-match
    # score, etc.) captured alongside the output — this is what the
    # Explainability Drawer shows for "why is this zone red."
    contributing_factors: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Populated only when source == llm_narrative.
    narrative: Mapped[str | None] = mapped_column(nullable=True)

    zone: Mapped["Zone"] = relationship(back_populates="risk_scores")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RiskScore zone={self.zone_id} score={self.score}>"
