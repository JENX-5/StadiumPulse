"""
Password hashing and JWT helpers.

Kept separate from `app/api/auth.py` (which owns the FastAPI-facing
dependencies: `get_current_user`, `RequireRole`) so the low-level crypto
primitives are independently testable and reusable from `db/seed.py`-style
scripts without pulling in FastAPI request machinery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

# Same scheme as `db/seed.py` so hashes generated there validate here.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT "type" claim distinguishes access tokens from any future refresh-token
# support and prevents a token minted for one purpose being replayed as another.
ACCESS_TOKEN_TYPE = "access"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    *,
    subject: uuid.UUID | str,
    role: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed JWT for `subject` (the user id).

    `role` is embedded in the payload so `RequireRole` checks don't need an
    extra DB round-trip beyond the `get_current_user` lookup that already
    happens for every request.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a JWT, raising `JWTError` on any failure
    (expired, bad signature, malformed, wrong type)."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise JWTError("Unexpected token type")
    return payload


__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
