"""
Authentication and Authorization dependencies.

Implements JWT token validation and Role-Based Access Control (RBAC)
checking for the FastAPI routers. Token *issuance* lives in
`app/api/v1/endpoints/auth.py` (the `/auth/token` route); this module only
verifies tokens presented on subsequent requests.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_db
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.security import JWTError, decode_access_token
from app.db.models.user import User, UserRole

# tokenUrl is the *full* mounted path (settings.api_v1_prefix + "/auth/token"),
# not just "token" — Swagger UI's "Authorize" button resolves this relative to
# the server root, so it must match the actual route registered in router.py.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().api_v1_prefix}/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Decode the bearer JWT, then load and return the corresponding user.

    Raises `UnauthorizedError` for any failure mode (missing token, expired,
    bad signature, malformed subject claim, or a subject that no longer
    maps to an active user) so callers get a uniform 401 regardless of
    *why* the token didn't validate.
    """
    settings = get_settings()

    try:
        payload = decode_access_token(token, settings)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise UnauthorizedError("Invalid token payload")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid token")

    return user


class RequireRole:
    """
    Dependency class to enforce RBAC on specific routes.
    Example: `Depends(RequireRole(UserRole.DISPATCHER))`
    """
    def __init__(self, allowed_roles: UserRole | list[UserRole]) -> None:
        if isinstance(allowed_roles, UserRole):
            self.allowed_roles = [allowed_roles]
        else:
            self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in self.allowed_roles and current_user.role != UserRole.ADMIN:
            raise ForbiddenError(f"Role {current_user.role} is not authorized to perform this action.")
        return current_user
