"""
User: authentication + RBAC identity.

`role` drives the API-layer authorization checks (Phase 6 review: role
checks are per-endpoint). `venue_id` is nullable because a platform-level
admin (multi-venue analytics, Phase 1 P1-flagged feature) is not scoped to
a single venue, while every other role is.
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

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.resource import Resource
    from app.db.models.venue import Venue


class UserRole(StrEnum):
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    VOLUNTEER = "volunteer"
    FAN = "fan"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserRole.FAN
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    venue: Mapped["Venue | None"] = relationship(back_populates="users")
    resource_profile: Mapped["Resource | None"] = relationship(
        back_populates="assigned_user", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} ({self.role})>"
