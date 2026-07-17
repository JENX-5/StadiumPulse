import uuid
from typing import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.implementations.incident_analysis import IncidentAnalysisAgent
from app.agents.implementations.operational_consensus import OperationalConsensusAgent
from app.agents.implementations.predictive_intelligence import PredictiveIntelligenceAgent
from app.agents.implementations.resource_coordination import ResourceCoordinationAgent
from app.agents.implementations.tournament_memory import TournamentMemoryAgent
from app.agents.types import AgentContext, AgentRequest, AgentTaskStatus
from app.core.config import get_settings
from app.core.events import Event, EventChannel
from app.core.llm_client import LLMClient
from app.db.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.db.models.negotiation import Negotiation, NegotiationPhase
from app.db.models.resource import ResourceStatus
from app.db.models.tournament_memory import TournamentMemory
from app.repositories.incident import incident_repo
from app.repositories.stadium import resource_repo
from app.schemas.event import IncidentCreatedPayload, IncidentUpdatedPayload
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.embeddings import generate_embedding
from app.services.event_bus import EventBus
from app.services.risk_scoring import RiskScoringService

logger = structlog.get_logger(__name__)

# Caps how many candidate resources are ever shown to the LLM in one prompt --
# mirrors `RAW_TEXT_MAX_LENGTH`'s "bound prompt size/cost" rationale
# (db/models/incident.py) applied to the resource-ranking call specifically.
MAX_CANDIDATE_RESOURCES = 20


class IncidentService:
    """Service layer for Incident management.

    Coordinates business logic, database persistence via the repository,
    the multi-agent analysis/recommendation pipeline, and side-effects
    (publishing to the Event Bus).
    """

    def __init__(
        self,
        event_bus: EventBus,
        llm_client: LLMClient,
        risk_scoring_service: RiskScoringService | None = None,
    ):
        self.event_bus = event_bus
        self.llm_client = llm_client
        self.risk_scoring_service = risk_scoring_service

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
        """Create a new incident, run the multi-agent analysis/recommendation
        pipeline against it, and publish the incident.created event."""
        db_obj = await incident_repo.create(db=db, obj_in=incident_in.model_dump())

        try:
            await self._run_agent_pipeline(db, db_obj)
        except Exception as exc:  # noqa: BLE001 - the pipeline must never block incident creation
            logger.error("agent_pipeline_failed", incident_id=str(db_obj.id), error=str(exc))

        payload = IncidentCreatedPayload(
            incident_id=str(db_obj.id),
            venue_id=str(db_obj.venue_id),
            status=db_obj.status.value,
            severity=db_obj.severity.value,
            raw_text=db_obj.raw_text,
        )
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
        updated_obj = await incident_repo.update(
            db=db, db_obj=db_obj, obj_in=update_in.model_dump(exclude_unset=True)
        )

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

    # -- Multi-agent pipeline -------------------------------------------------
    #
    # Each stage is independently fault-tolerant: a failed/skipped agent
    # leaves its slot in `structured_summary` empty rather than aborting the
    # whole pipeline, matching every agent's own documented fallback
    # contract (see agents/base.py and agents/implementations/*.py).

    async def _run_agent_pipeline(self, db: AsyncSession, db_obj: Incident) -> None:
        venue_id = str(db_obj.venue_id)
        context = AgentContext(venue_id=venue_id)

        analysis_data = await self._run_incident_analysis(db_obj)
        if analysis_data:
            self._apply_analysis(db_obj, analysis_data)

        (
            recommendation,
            recommendation_confidence,
            recommendation_rationale,
        ) = await self._run_resource_coordination(db, db_obj, analysis_data, context)
        if recommendation:
            await self._record_negotiation_turn(
                db,
                incident_id=db_obj.id,
                turn_number=1,
                phase=NegotiationPhase.PROPOSAL,
                agent_name="resource_coordination",
                content=recommendation,
                rationale=recommendation_rationale,
            )

        consensus = await self._run_operational_consensus(
            recommendation, recommendation_confidence, recommendation_rationale, context
        )
        if consensus:
            await self._record_negotiation_turn(
                db,
                incident_id=db_obj.id,
                turn_number=2,
                phase=NegotiationPhase.RESOLUTION,
                agent_name="operational_consensus",
                content=consensus,
                rationale=consensus.get("rationale"),
            )

        narrative = await self._run_predictive_intelligence(db_obj, context)

        db_obj.structured_summary = {
            **(db_obj.structured_summary or {}),
            "analysis": analysis_data or None,
            "recommended_resources": recommendation or None,
            "consensus": consensus or None,
            "risk_narrative": narrative,
        }
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        if consensus:
            await self._run_tournament_memory(db, db_obj, analysis_data, consensus)

    async def _run_incident_analysis(self, db_obj: Incident) -> dict:
        agent = IncidentAnalysisAgent(llm_client=self.llm_client)
        result = await agent.execute(
            AgentRequest(task_type="incident_analysis", input_data={"raw_text": db_obj.raw_text})
        )
        if result.status != AgentTaskStatus.SUCCEEDED or not result.output:
            logger.warning(
                "incident_analysis_agent_failed",
                incident_id=str(db_obj.id),
                error=result.error_message,
            )
            return {}
        return result.output.data

    def _apply_analysis(self, db_obj: Incident, analysis_data: dict) -> None:
        severity_str = str(analysis_data.get("severity", "medium")).upper()
        try:
            db_obj.severity = IncidentSeverity[severity_str]
        except KeyError:
            db_obj.severity = IncidentSeverity.MEDIUM

    async def _fetch_available_resources(self, db: AsyncSession, db_obj: Incident) -> list[dict]:
        """Deterministic SQL pre-filter (venue + status=available) -- the LLM
        is only ever shown resources this query already selected, never
        asked to guess or invent a candidate itself."""
        resources = await resource_repo.get_by_venue(
            db, db_obj.venue_id, status=ResourceStatus.AVAILABLE
        )
        serialized = [
            {
                "id": str(r.id),
                "label": r.label,
                "resource_type": r.resource_type.value,
                "status": r.status.value,
                "same_zone": bool(db_obj.zone_id) and r.current_zone_id == db_obj.zone_id,
            }
            for r in resources
        ]
        # Same-zone candidates first so the ranking prompt sees the most
        # relevant options within the token budget below.
        serialized.sort(key=lambda r: not r["same_zone"])
        return serialized[:MAX_CANDIDATE_RESOURCES]

    async def _run_resource_coordination(
        self,
        db: AsyncSession,
        db_obj: Incident,
        analysis_data: dict,
        context: AgentContext,
    ) -> tuple[dict, float, str | None]:
        available_resources = await self._fetch_available_resources(db, db_obj)
        if not available_resources:
            logger.info(
                "resource_coordination_skipped_no_available_resources", incident_id=str(db_obj.id)
            )
            return {}, 0.0, None

        agent = ResourceCoordinationAgent(llm_client=self.llm_client)
        result = await agent.execute(
            AgentRequest(
                task_type="rank_resources",
                input_data={
                    "incident": analysis_data or {"raw_text": db_obj.raw_text},
                    "available_resources": available_resources,
                },
                context=context,
            )
        )
        if result.status != AgentTaskStatus.SUCCEEDED or not result.output:
            logger.warning(
                "resource_coordination_agent_failed",
                incident_id=str(db_obj.id),
                error=result.error_message,
            )
            return {}, 0.0, None
        return result.output.data, result.output.confidence, result.output.rationale

    async def _run_operational_consensus(
        self,
        recommendation: dict,
        recommendation_confidence: float,
        recommendation_rationale: str | None,
        context: AgentContext,
    ) -> dict:
        if not recommendation:
            return {}

        agent = OperationalConsensusAgent(llm_client=self.llm_client)
        messages = [
            {
                "turn_number": 1,
                "phase": "proposal",
                "agent_id": "resource_coordination",
                "content": recommendation,
                "confidence": recommendation_confidence,
                "rationale": recommendation_rationale,
            }
        ]
        result = await agent.execute(
            AgentRequest(
                task_type="resolve_consensus", input_data={"messages": messages}, context=context
            )
        )
        if result.status != AgentTaskStatus.SUCCEEDED or not result.output:
            logger.warning("operational_consensus_agent_failed", error=result.error_message)
            return {}
        return result.output.data

    async def _run_predictive_intelligence(
        self, db_obj: Incident, context: AgentContext
    ) -> str | None:
        """Only invoked when the incident's zone has a real current risk
        score on record (ADR-0001) -- never called with synthetic data just
        to keep this slot non-empty."""
        if not db_obj.zone_id or not self.risk_scoring_service:
            return None

        score_result = await self.risk_scoring_service.get_current_score(str(db_obj.zone_id))
        if not score_result:
            return None

        agent = PredictiveIntelligenceAgent(llm_client=self.llm_client)
        result = await agent.execute(
            AgentRequest(
                task_type="generate_narrative",
                input_data={
                    "zone_id": str(db_obj.zone_id),
                    "risk_score": score_result.score,
                    "contributing_factors": score_result.contributing_factors,
                },
                context=context,
            )
        )
        if result.status != AgentTaskStatus.SUCCEEDED or not result.output:
            logger.warning(
                "predictive_intelligence_agent_failed",
                incident_id=str(db_obj.id),
                error=result.error_message,
            )
            return None
        return result.output.data.get("narrative")

    async def _run_tournament_memory(
        self, db: AsyncSession, db_obj: Incident, analysis_data: dict, consensus: dict
    ) -> None:
        agent = TournamentMemoryAgent(llm_client=self.llm_client)
        result = await agent.execute(
            AgentRequest(
                task_type="generate_memory",
                input_data={
                    "incident": analysis_data or {"raw_text": db_obj.raw_text},
                    "decision": consensus,
                },
                context=AgentContext(venue_id=str(db_obj.venue_id)),
            )
        )
        if result.status != AgentTaskStatus.SUCCEEDED or not result.output:
            logger.warning(
                "tournament_memory_agent_failed",
                incident_id=str(db_obj.id),
                error=result.error_message,
            )
            return

        summary = result.output.data.get("memory_summary", "")
        if not summary:
            return

        settings = get_settings()
        embedding = await generate_embedding(summary, settings)
        db.add(
            TournamentMemory(
                venue_id=db_obj.venue_id,
                summary=summary,
                pattern_type=analysis_data.get("incident_type", "other"),
                embedding=embedding,
                source_incident_ids=[db_obj.id],
                metadata_={
                    "severity": db_obj.severity.value,
                    "consensus_outcome": consensus.get("outcome"),
                },
            )
        )
        await db.commit()

    async def _record_negotiation_turn(
        self,
        db: AsyncSession,
        *,
        incident_id: uuid.UUID,
        turn_number: int,
        phase: NegotiationPhase,
        agent_name: str,
        content: dict,
        rationale: str | None,
    ) -> None:
        """Persists one row of the negotiation transcript the Explainability
        Drawer reads (see db/models/negotiation.py's docstring)."""
        db.add(
            Negotiation(
                incident_id=incident_id,
                phase=phase,
                turn_number=turn_number,
                agent_name=agent_name,
                content=content,
                rationale=rationale,
            )
        )
        await db.commit()
