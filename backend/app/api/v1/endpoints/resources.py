"""
Resources API endpoints.
"""


import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, RequireRole
from app.core.dependencies import get_db, get_container
from app.core.container import Container
from app.db.models.resource import Resource, ResourceStatus
from app.db.models.user import User, UserRole


router = APIRouter()


@router.get("/")
async def list_resources(
    venue_id: uuid.UUID,
    status: ResourceStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List resources for a venue, optionally filtered by status."""
    stmt = select(Resource).where(Resource.venue_id == venue_id)
    if status:
        stmt = stmt.where(Resource.status == status)
        
    result = await db.execute(stmt)
    resources = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "label": r.label,
            "resource_type": r.resource_type,
            "status": r.status,
            "current_zone_id": str(r.current_zone_id) if r.current_zone_id else None,
        }
        for r in resources
    ]


@router.post("/{resource_id}/dispatch")
async def dispatch_resource(
    resource_id: uuid.UUID,
    incident_id: uuid.UUID,
    container: Container = Depends(get_container),
    current_user: User = Depends(RequireRole(UserRole.DISPATCHER)),
) -> dict:
    """Manually dispatch a resource to an incident."""
    assignment = await container.dispatch_service.dispatch_resource(
        incident_id=incident_id,
        resource_id=resource_id,
        assigned_by=f"user:{current_user.id}"
    )
    
    return {
        "id": str(assignment.id),
        "incident_id": str(assignment.incident_id),
        "resource_id": str(assignment.resource_id),
        "status": assignment.status,
    }
