import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import Event, EventChannel
from app.db.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.repositories.incident import incident_repo
from app.schemas.event import IncidentCreatedPayload, IncidentUpdatedPayload
from app.agents.implementations.incident_analysis import IncidentAnalysisAgent
from app.agents.types import AgentRequest
from app.core.llm_client import LLMClient
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.event_bus import EventBus


class IncidentService:
    """Service layer for Incident management.
    
    Coordinates business logic, database persistence via the repository,
    and side-effects (publishing to the Event Bus).
    """

    def __init__(self, event_bus: EventBus, llm_client: LLMClient):
        self.event_bus = event_bus
        self.llm_client = llm_client

    async def get_incident(self, db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
        return await incident_repo.get(db=db, id=incident_id)

    async def get_incidents_by_venue(
        self,
        db: AsyncSession,
        venue_id: uuid.UUID,
        status: IncidentStatus | None = None,
        severity: IncidentSeverity | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Incident]:
        return await incident_repo.get_by_venue(
            db=db, venue_id=venue_id, status=status, severity=severity, skip=skip, limit=limit
        )

    async def create_incident(self, db: AsyncSession, incident_in: IncidentCreate) -> Incident:
        """Create a new incident and publish the incident.created event."""
        # 1. Persist to DB
        db_obj = await incident_repo.create(db=db, obj_in=incident_in.model_dump())
        
        # 1.5 Analyze with LLM Agent
        try:
            agent = IncidentAnalysisAgent(llm_client=self.llm_client)
            req = AgentRequest(
                task_type="incident_analysis",
                input_data={"raw_text": db_obj.raw_text}
            )
            result = await agent.execute(req)
            
            if result.status == "succeeded" and result.output:
                severity_str = result.output.data.get("severity", "medium").upper()
                try:
                    db_obj.severity = IncidentSeverity[severity_str]
                except KeyError:
                    db_obj.severity = IncidentSeverity.MEDIUM
                    
                db_obj.structured_summary = result.output.data
                
                # Save the updates
                db.add(db_obj)
                await db.commit()
                await db.refresh(db_obj)
        except Exception as e:
            import logging
            logging.error(f"IncidentAnalysisAgent failed: {e}")
        
        # 2. Construct Domain Event Payload
        payload = IncidentCreatedPayload(
            incident_id=str(db_obj.id),
            venue_id=str(db_obj.venue_id),
            status=db_obj.status.value,
            severity=db_obj.severity.value,
            raw_text=db_obj.raw_text,
        )
        
        # 3. Publish to Event Bus
        event = Event(
            event_type="incident.created",
            source=db_obj.source,
            venue_id=str(db_obj.venue_id),
            payload=payload.model_dump(),
        )
        await self.event_bus.publish(EventChannel.INCIDENTS, event)
        
        return db_obj

    async def update_incident(
        self, db: AsyncSession, db_obj: Incident, update_in: IncidentUpdate
    ) -> Incident:
        """Update an incident and publish the incident.updated event."""
        # Update DB using only the fields explicitly provided in the request
        updated_obj = await incident_repo.update(
            db=db, db_obj=db_obj, obj_in=update_in.model_dump(exclude_unset=True)
        )
        
        # Construct and publish event
        payload = IncidentUpdatedPayload(
            incident_id=str(updated_obj.id),
            venue_id=str(updated_obj.venue_id),
            status=updated_obj.status.value,
            severity=updated_obj.severity.value,
        )
        
        event = Event(
            event_type="incident.updated",
            source=updated_obj.source,
            venue_id=str(updated_obj.venue_id),
            payload=payload.model_dump(),
        )
        await self.event_bus.publish(EventChannel.INCIDENTS, event)
        
        return updated_obj
