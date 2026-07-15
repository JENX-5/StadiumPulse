"""
Application-wide dependency injection container.

A deliberately lightweight container (no DI framework) holding process-level
singletons: settings, DB engine/session factory, Redis client, and the
shared LLMClient. FastAPI routes and agent constructors receive these via
`Depends(get_container)` / explicit constructor injection rather than
importing globals directly — this is what makes every module unit-testable
in isolation (swap in a fake LLMClient, an in-memory session factory, etc).

The container is created once in `main.py`'s lifespan handler and attached
to `app.state.container`.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agents.implementations.incident_analysis import IncidentAnalysisAgent
from app.agents.implementations.operational_consensus import OperationalConsensusAgent
from app.agents.implementations.predictive_intelligence import PredictiveIntelligenceAgent
from app.agents.implementations.resource_coordination import ResourceCoordinationAgent
from app.agents.implementations.tournament_memory import TournamentMemoryAgent
from app.agents.registry import AgentRegistry
from app.core.config import Settings
from app.core.llm_client import LLMClient
from app.core.llm_providers import build_llm_client
from app.db.session import create_engine, create_session_factory
from app.services.dispatch import DispatchService
from app.services.event_bus import EventBus
from app.services.notification import NotificationInfrastructure
from app.services.risk_scoring import RiskScoringService
from app.services.simulation import SimulationEngine
from app.services.state import OperationalStateManager
from app.services.timeline import TimelineEngine

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class Container:
    """Holds every process-level singleton the application depends on."""

    settings: Settings
    db_engine: AsyncEngine
    db_session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    llm_client: LLMClient
    agent_registry: AgentRegistry
    event_bus: EventBus
    state_manager: OperationalStateManager
    timeline_engine: TimelineEngine
    notification_infra: NotificationInfrastructure
    simulation_engine: SimulationEngine
    risk_scoring_service: RiskScoringService
    dispatch_service: DispatchService

    async def shutdown(self) -> None:
        """Release external resources cleanly on application shutdown."""
        await self.risk_scoring_service.close()
        await self.event_bus.redis.aclose()
        await self.state_manager.redis.aclose()
        await self.timeline_engine.redis.aclose()
        await self.notification_infra.redis.aclose()
        await self.redis.aclose()
        await self.db_engine.dispose()
        logger.info("container_shutdown_complete")


async def build_container(settings: Settings) -> Container:
    """Construct and connectivity-check every singleton the app needs.

    Raising here (rather than lazily on first use) means a broken DB or
    Redis connection fails fast at startup — never mid-request during a
    demo.
    """
    db_engine = create_engine(settings)
    db_session_factory = create_session_factory(db_engine)

    redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)

    llm_client: LLMClient = build_llm_client(settings)

    event_bus = EventBus(redis_url=settings.redis_url)
    state_manager = OperationalStateManager(redis_url=settings.redis_url)
    timeline_engine = TimelineEngine(redis_url=settings.redis_url)
    notification_infra = NotificationInfrastructure(redis_url=settings.redis_url)
    simulation_engine = SimulationEngine(event_bus=event_bus)
    # Only Redis-backed service that also needs Postgres — history is
    # write-through per ADR-0004, so it takes the shared session factory
    # rather than talking to Postgres via a route/service of its own.
    risk_scoring_service = RiskScoringService(
        redis_url=settings.redis_url,
        db_session_factory=db_session_factory,
    )
    dispatch_service = DispatchService(session_factory=db_session_factory)

    agent_registry = AgentRegistry()
    # Registered here rather than at import time so every agent gets the
    # same request-scoped-free singletons (llm_client, etc.) the rest of
    # the container uses — remaining agents (PIA, RCA, OCA, TMA) register
    # the same way as their modules land.
    agent_registry.register(IncidentAnalysisAgent(llm_client=llm_client))
    agent_registry.register(OperationalConsensusAgent(llm_client=llm_client))
    agent_registry.register(PredictiveIntelligenceAgent(llm_client=llm_client))
    agent_registry.register(ResourceCoordinationAgent(llm_client=llm_client))
    agent_registry.register(TournamentMemoryAgent(llm_client=llm_client))

    container = Container(
        settings=settings,
        db_engine=db_engine,
        db_session_factory=db_session_factory,
        redis=redis_client,
        llm_client=llm_client,
        agent_registry=agent_registry,
        event_bus=event_bus,
        state_manager=state_manager,
        timeline_engine=timeline_engine,
        notification_infra=notification_infra,
        simulation_engine=simulation_engine,
        risk_scoring_service=risk_scoring_service,
        dispatch_service=dispatch_service,
    )
    logger.info("container_built", env=settings.env)
    return container
