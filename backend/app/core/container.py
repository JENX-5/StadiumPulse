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

from app.agents.registry import AgentRegistry
from app.core.config import Settings
from app.core.llm_client import LLMClient
from app.core.llm_providers import build_llm_client
from app.db.session import create_engine, create_session_factory
from app.services.event_bus import EventBus
from app.services.notification import NotificationInfrastructure
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

    async def shutdown(self) -> None:
        """Release external resources cleanly on application shutdown."""
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

    # Empty at this stage — Module 3 provides the registry infrastructure
    # only. Concrete agents (Predictive Intelligence, Incident Analysis,
    # etc.) call `container.agent_registry.register(...)` from their own
    # module's startup wiring once they exist.
    agent_registry = AgentRegistry()

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
    )
    logger.info("container_built", env=settings.env)
    return container
