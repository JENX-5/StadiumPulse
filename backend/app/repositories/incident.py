import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    """Repository for managing Incident records."""

    def __init__(self):
        super().__init__(Incident)

    async def get_by_venue(
        self,
        db: AsyncSession,
        venue_id: uuid.UUID,
        *,
        status: IncidentStatus | None = None,
        severity: IncidentSeverity | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Incident]:
        """Fetch incidents filtered by venue, status, and severity."""
        stmt = select(self.model).filter(self.model.venue_id == venue_id)
        
        if status:
            stmt = stmt.filter(self.model.status == status)
        if severity:
            stmt = stmt.filter(self.model.severity == severity)
            
        # Return newest incidents first
        stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()


# Singleton instance
incident_repo = IncidentRepository()
