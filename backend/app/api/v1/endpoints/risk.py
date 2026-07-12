"""
Risk API endpoints.
"""


import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.core.dependencies import get_container
from app.core.container import Container
from app.db.models.user import User


router = APIRouter()


@router.get("/{venue_id}/heatmap")
async def get_risk_heatmap(
    venue_id: uuid.UUID,
    container: Container = Depends(get_container),
    current_user: User = Depends(get_current_user),
) -> dict[str, float]:
    """
    Get the hot read-path risk heatmap for a venue.
    Returns a dictionary of zone_id to risk_score.
    """
    # RiskScoringService reads from Redis
    heatmap = await container.risk_scoring_service.get_heatmap(str(venue_id))
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
    score, factors = await container.risk_scoring_service.get_zone_risk(str(venue_id), str(zone_id))
    return {
        "zone_id": str(zone_id),
        "risk_score": score,
        "contributing_factors": factors,
    }
