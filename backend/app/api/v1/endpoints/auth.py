"""
Auth API endpoints: token issuance and current-user profile lookup.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.db.models.user import User
from app.schemas.auth import Token, UserProfile

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Token:
    """
    OAuth2-compatible token login.

    Strictly form-encoded per the OAuth2 password grant spec (this is what
    populates FastAPI's `/docs` "Authorize" button and what
    `OAuth2PasswordBearer` expects downstream) — `form_data.username` is the
    user's email, `form_data.password` is their plaintext password.
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        # Same error for "no such user" and "wrong password" — don't leak
        # which one it was.
        raise UnauthorizedError("Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")

    access_token = create_access_token(subject=user.id, role=user.role.value, settings=settings)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserProfile)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return the profile of the user identified by the bearer token."""
    return current_user
