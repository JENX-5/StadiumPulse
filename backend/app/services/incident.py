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
        
        # 1.5 Analyze with LLM Agent Pipeline (Full 5-Agent Debate)
        try:
            from app.agents.implementations.incident_analysis import IncidentAnalysisAgent
            from app.agents.implementations.predictive_intelligence import PredictiveIntelligenceAgent
            from app.agents.implementations.resource_coordination import ResourceCoordinationAgent
            from app.agents.implementations.operational_consensus import OperationalConsensusAgent
            from app.agents.implementations.tournament_memory import TournamentMemoryAgent
            from app.agents.types import AgentContext, AgentRequest
            
            # Agent 1: Incident Analysis
            ia_agent = IncidentAnalysisAgent(llm_client=self.llm_client)
            req = AgentRequest(
                task_type="incident_analysis",
                input_data={"raw_text": db_obj.raw_text}
            )
            ia_result = await ia_agent.execute(req)
            
            shared_ctx = {}
            if ia_result.status == "succeeded" and ia_result.output:
                severity_str = ia_result.output.data.get("severity", "medium").upper()
                try:
                    db_obj.severity = IncidentSeverity[severity_str]
                except KeyError:
                    db_obj.severity = IncidentSeverity.MEDIUM
                    
                db_obj.structured_summary = ia_result.output.data
                shared_ctx["incident_analysis"] = ia_result.output.data
            
            # Agent 2: Predictive Intelligence
            pi_agent = PredictiveIntelligenceAgent(llm_client=self.llm_client)
            pi_req = AgentRequest(
                task_type="predict_risk",
                input_data={"current_state": shared_ctx.get("incident_analysis", {})},
                context=AgentContext(venue_id=str(db_obj.venue_id), shared_variables=shared_ctx)
            )
            pi_result = await pi_agent.execute(pi_req)
            
            # Agent 3: Resource Coordination
            rc_agent = ResourceCoordinationAgent(llm_client=self.llm_client)
            rc_req = AgentRequest(
                task_type="coordinate_resources",
                input_data={"incident_details": shared_ctx.get("incident_analysis", {})},
                context=AgentContext(venue_id=str(db_obj.venue_id), shared_variables=shared_ctx)
            )
            rc_result = await rc_agent.execute(rc_req)
            
            # Agent 4: Operational Consensus
            oc_agent = OperationalConsensusAgent(llm_client=self.llm_client)
            messages = [
                {"turn_number": 1, "phase": "proposal", "agent_id": "resource_coordination", "content": rc_result.output.data if rc_result.output else {}},
                {"turn_number": 2, "phase": "proposal", "agent_id": "predictive_intelligence", "content": pi_result.output.data if pi_result.output else {}}
            ]
            oc_req = AgentRequest(
                task_type="resolve_consensus",
                input_data={"messages": messages},
                context=AgentContext(venue_id=str(db_obj.venue_id), shared_variables=shared_ctx)
            )
            oc_result = await oc_agent.execute(oc_req)
            
            # Agent 5: Tournament Memory
            tm_agent = TournamentMemoryAgent(llm_client=self.llm_client)
            tm_req = AgentRequest(
                task_type="store_memory",
                input_data={"incident_id": str(db_obj.id), "resolution": oc_result.output.data if oc_result.output else {}},
                context=AgentContext(venue_id=str(db_obj.venue_id), shared_variables=shared_ctx)
            )
            await tm_agent.execute(tm_req)

            # Save the updates
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
        except Exception as e:
            import logging
            logging.error(f"Multi-Agent Pipeline failed: {e}")
        
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
