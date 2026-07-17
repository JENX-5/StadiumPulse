"""
Memory API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.dependencies import get_db
from app.db.models.tournament_memory import TournamentMemory
from app.db.models.user import User

router = APIRouter()


@router.get("/")
async def list_memories(
    venue_id: uuid.UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    List recent memories for a venue.
    """
    stmt = (
        select(TournamentMemory)
        .where(TournamentMemory.venue_id == venue_id)
        .order_by(TournamentMemory.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    memories = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "summary": m.summary,
            "pattern_type": m.pattern_type,
            "source_incident_ids": [str(i) for i in m.source_incident_ids],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memories
    ]
