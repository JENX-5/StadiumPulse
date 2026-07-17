"""
Risk API endpoints.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.container import Container
from app.core.dependencies import get_container, get_db
from app.db.models.user import User
from app.repositories.stadium import zone_repo

router = APIRouter()


@router.get("/{venue_id}/heatmap")
async def get_risk_heatmap(
    venue_id: uuid.UUID,
    container: Container = Depends(get_container),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, float]:
    """
    Get the hot read-path risk heatmap for a venue.
    Returns a dictionary of zone_id to risk_score.
    """
    zones = await zone_repo.get_by_venue(db, venue_id)
    zone_ids = [str(zone.id) for zone in zones]
    scores = await container.risk_scoring_service.get_venue_scores(str(venue_id), zone_ids)

    heatmap = {str(zone.id): 0.0 for zone in zones}
    for zid, result in scores.items():
        heatmap[zid] = result.score

    return heatmap


@router.get("/{venue_id}/zones/{zone_id}")
async def get_zone_risk(
    venue_id: uuid.UUID,
    zone_id: uuid.UUID,
    container: Container = Depends(get_container),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get the detailed risk score and contributing factors for a specific zone.
    """
    result = await container.risk_scoring_service.get_current_score(str(zone_id))
    if result is None:
        return {
            "zone_id": str(zone_id),
            "risk_score": 0.0,
            "contributing_factors": {},
        }

    return {
        "zone_id": str(zone_id),
        "risk_score": result.score,
        "contributing_factors": result.contributing_factors,
    }
