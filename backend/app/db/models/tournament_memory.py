"""
TournamentMemory: embeddings + summaries the Tournament Memory Agent writes
asynchronously after an incident resolves, and later queries via pgvector
similarity search to recognize "we've seen this pattern before" — the
in-session "learning" moment the product's demo relies on.

Embedding dimension (1024) matches a typical lightweight embedding model
(the review notes this is deliberately a separate, smaller model from the
reasoning LLM). If the embedding provider changes, this column's dimension
must change via migration — it is not dynamically sized.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.venue import Venue

EMBEDDING_DIMENSION = 1024


class TournamentMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_memory"
    __table_args__ = (
        # IVFFlat approximate nearest-neighbor index — sufficient at hackathon/
        # single-tournament scale. `lists` is intentionally small; revisit if
        # memory volume grows into the tens of thousands of rows.
        Index(
            "ix_tournament_memory_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(nullable=False)
    pattern_type: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    # Source incidents this memory was distilled from — kept as a plain
    # array of UUIDs rather than a join table since this is written once,
    # read-only afterward, and never needs to be queried "from the incident
    # side" (the incident doesn't need to know which memories cite it).
    source_incident_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    venue: Mapped["Venue"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TournamentMemory {self.pattern_type} venue={self.venue_id}>"
