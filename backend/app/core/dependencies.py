"""
FastAPI dependency-injection glue.

Bridges FastAPI's `Depends()` system to the process-level `Container` built
once at startup (see `core/container.py`). Routes depend on `get_container`
(or a narrower accessor below) rather than importing the container global
directly, which keeps route handlers trivially testable via
`app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import Container
from app.core.llm_client import LLMClient
from app.db.session import session_scope
from app.services.event_bus import EventBus
from app.services.incident import IncidentService
from app.services.notification import NotificationInfrastructure
from app.services.simulation import SimulationEngine
from app.services.state import OperationalStateManager
from app.services.timeline import TimelineEngine


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_llm_client(
    container: Annotated[Container, Depends(get_container)],
) -> LLMClient:
    return container.llm_client


async def get_db(
    container: Annotated[Container, Depends(get_container)],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_scope(container.db_session_factory) as session:
        yield session


def get_event_bus(container: Annotated[Container, Depends(get_container)]) -> EventBus:
    return container.event_bus


def get_state_manager(container: Annotated[Container, Depends(get_container)]) -> OperationalStateManager:
    return container.state_manager


def get_timeline_engine(container: Annotated[Container, Depends(get_container)]) -> TimelineEngine:
    return container.timeline_engine


def get_notification_infra(container: Annotated[Container, Depends(get_container)]) -> NotificationInfrastructure:
    return container.notification_infra


def get_simulation_engine(container: Annotated[Container, Depends(get_container)]) -> SimulationEngine:
    return container.simulation_engine


def get_incident_service(
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> IncidentService:
    return IncidentService(event_bus=event_bus, llm_client=llm_client)
