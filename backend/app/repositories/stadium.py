import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resource import Resource, ResourceStatus, ResourceType
from app.db.models.venue import Venue
from app.db.models.zone import Zone
from app.repositories.base import BaseRepository


class VenueRepository(BaseRepository[Venue]):
    """Repository for Venues."""
    def __init__(self):
        super().__init__(Venue)


class ZoneRepository(BaseRepository[Zone]):
    """Repository for Zones."""
    def __init__(self):
        super().__init__(Zone)
        
    async def get_by_venue(self, db: AsyncSession, venue_id: uuid.UUID) -> Sequence[Zone]:
        """Fetch all zones for a specific venue."""
        result = await db.execute(select(self.model).filter(self.model.venue_id == venue_id))
        return result.scalars().all()


class ResourceRepository(BaseRepository[Resource]):
    """Repository for Resources (Medical, Security, etc)."""
    def __init__(self):
        super().__init__(Resource)
        
    async def get_by_venue(
        self, 
        db: AsyncSession, 
        venue_id: uuid.UUID,
        *,
        status: ResourceStatus | None = None,
        resource_type: ResourceType | None = None
    ) -> Sequence[Resource]:
        """Fetch resources filtered by venue, status, and type."""
        stmt = select(self.model).filter(self.model.venue_id == venue_id)
        
        if status:
            stmt = stmt.filter(self.model.status == status)
        if resource_type:
            stmt = stmt.filter(self.model.resource_type == resource_type)
            
        result = await db.execute(stmt)
        return result.scalars().all()


# Singleton instances
venue_repo = VenueRepository()
zone_repo = ZoneRepository()
resource_repo = ResourceRepository()
