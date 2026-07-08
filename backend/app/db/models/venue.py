"""Venue: the top-level tenant boundary. Every other domain table hangs off a venue_id."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.incident import Incident
    from app.db.models.resource import Resource
    from app.db.models.user import User
    from app.db.models.zone import Zone


class Venue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "venues"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    zones: Mapped[list["Zone"]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="venue")
    resources: Mapped[list["Resource"]] = relationship(back_populates="venue")
    users: Mapped[list["User"]] = relationship(back_populates="venue")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Venue {self.name}>"
