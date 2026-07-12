"""Auth-related request/response schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.db.models.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: uuid.UUID
    role: UserRole
    exp: int


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    venue_id: uuid.UUID | None
    is_active: bool
