"""
Authentication and Authorization dependencies.

Implements token validation and Role-Based Access Control (RBAC) checking
for the FastAPI routers.
"""


from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.dependencies import get_db, get_container
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.db.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validates the token and returns the current user.
    For this module, we use a simplistic token -> user mapping or mock.
    """
    # In a real app, you would decode a JWT here.
    # For now, we assume the token is the user's UUID or email for testing/demo.
    if not token:
        raise UnauthorizedError("Missing token")
        
    # Attempt to look up the user by ID (assuming token is ID for now)
    try:
        stmt = select(User).where(User.id == token)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        user = None

    if not user:
        # Fallback for local testing without valid UUIDs
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
