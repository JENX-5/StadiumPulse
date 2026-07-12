"""
Zones API endpoints.

`ZoneRepository.get_by_venue` and `ZoneResponse` already existed (see
`app/repositories/stadium.py`, `app/schemas/stadium.py`) but had no route
wired up — the frontend needs this to populate zone pickers (simulation
incident-injection, map zone drawer).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.dependencies import get_db
from app.db.models.user import User
from app.repositories.stadium import zone_repo
from app.schemas.stadium import ZoneResponse

router = APIRouter()


@router.get("/", response_model=list[ZoneResponse])
async def list_zones(
    venue_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ZoneResponse]:
    """List all zones for a venue."""
    return await zone_repo.get_by_venue(db, venue_id)
