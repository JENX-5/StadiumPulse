import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_incident_service
from app.db.models.incident import IncidentSeverity, IncidentStatus
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentUpdate
from app.services.incident import IncidentService

router = APIRouter()


@router.post("/", response_model=IncidentResponse, status_code=201)
async def create_incident(
    incident_in: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
):
    """Create a new incident and dispatch an event."""
    return await incident_service.create_incident(db, incident_in)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
):
    """Retrieve an incident by ID."""
    incident = await incident_service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/venue/{venue_id}", response_model=list[IncidentResponse])
async def get_incidents_by_venue(
    venue_id: uuid.UUID,
    status: IncidentStatus | None = None,
    severity: IncidentSeverity | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
):
    """List incidents for a given venue with optional filtering."""
    return await incident_service.get_incidents_by_venue(
        db, venue_id, status=status, severity=severity, skip=skip, limit=limit
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    update_in: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    incident_service: IncidentService = Depends(get_incident_service),
):
    """Update an incident (e.g. resolve it) and dispatch an event."""
    db_obj = await incident_service.get_incident(db, incident_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    return await incident_service.update_incident(db, db_obj=db_obj, update_in=update_in)
