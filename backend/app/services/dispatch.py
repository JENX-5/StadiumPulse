"""
Dispatch Service.

Responsible for writing to the `resource_assignments` table (ADR-0002).
Takes a resolved consensus decision (or manual override) and officially
dispatches resources to an incident.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.resource_assignment import AssignmentStatus, ResourceAssignment

logger = structlog.get_logger(__name__)


class DispatchService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def dispatch_resource(
        self,
        incident_id: str | uuid.UUID,
        resource_id: str | uuid.UUID,
        assigned_by: str = "dispatch_service",
    ) -> ResourceAssignment:
        """
        Officially assigns a resource to an incident.
        Only this service should insert rows into `resource_assignments`.
        """
        if isinstance(incident_id, str):
            incident_id = uuid.UUID(incident_id)
        if isinstance(resource_id, str):
            resource_id = uuid.UUID(resource_id)

        async with self._session_factory() as session:
            assignment = ResourceAssignment(
                incident_id=incident_id,
                resource_id=resource_id,
                status=AssignmentStatus.PENDING,
                assigned_by=assigned_by,
            )
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)

            logger.info(
                "resource_dispatched",
                incident_id=str(incident_id),
                resource_id=str(resource_id),
                assigned_by=assigned_by,
                assignment_id=str(assignment.id),
            )
            return assignment
