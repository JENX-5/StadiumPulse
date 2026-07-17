"""Tests for DispatchService (ADR-0002): the only module allowed to write
`resource_assignments` rows."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.db.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.db.models.resource import Resource, ResourceStatus, ResourceType
from app.db.models.resource_assignment import AssignmentStatus
from app.db.models.venue import Venue
from app.services.dispatch import DispatchService


async def _make_incident_and_resource(db_session) -> tuple[Incident, Resource]:
    venue = Venue(id=uuid.uuid4(), name="Test Venue", timezone="UTC")
    db_session.add(venue)
    await db_session.flush()

    incident = Incident(
        venue_id=venue.id,
        raw_text="Fight reported near Gate C",
        status=IncidentStatus.OPEN,
        severity=IncidentSeverity.HIGH,
    )
    resource = Resource(
        venue_id=venue.id,
        label="Unit 4",
        resource_type=ResourceType.SECURITY,
        status=ResourceStatus.AVAILABLE,
    )
    db_session.add_all([incident, resource])
    await db_session.commit()
    await db_session.refresh(incident)
    await db_session.refresh(resource)
    return incident, resource


@pytest.mark.asyncio
async def test_dispatch_resource_creates_pending_assignment(
    client: AsyncClient, db_session
) -> None:
    from app.main import app

    incident, resource = await _make_incident_and_resource(db_session)
    dispatch_service: DispatchService = app.state.container.dispatch_service

    assignment = await dispatch_service.dispatch_resource(
        incident_id=incident.id, resource_id=resource.id
    )

    assert assignment.id is not None
    assert assignment.incident_id == incident.id
    assert assignment.resource_id == resource.id
    assert assignment.status == AssignmentStatus.PENDING
    assert assignment.assigned_by == "dispatch_service"
    assert assignment.completed_at is None


@pytest.mark.asyncio
async def test_dispatch_resource_accepts_string_ids(client: AsyncClient, db_session) -> None:
    """incident_id/resource_id may arrive as strings (e.g. from an API payload
    or an agent's JSON output) rather than uuid.UUID instances."""
    from app.main import app

    incident, resource = await _make_incident_and_resource(db_session)
    dispatch_service: DispatchService = app.state.container.dispatch_service

    assignment = await dispatch_service.dispatch_resource(
        incident_id=str(incident.id), resource_id=str(resource.id)
    )

    assert assignment.incident_id == incident.id
    assert assignment.resource_id == resource.id


@pytest.mark.asyncio
async def test_dispatch_resource_records_manual_override_marker(
    client: AsyncClient, db_session
) -> None:
    """`assigned_by` distinguishes an automatic dispatch from a human admin
    override — both must be representable (see resource_assignment.py docstring)."""
    from app.main import app

    incident, resource = await _make_incident_and_resource(db_session)
    dispatch_service: DispatchService = app.state.container.dispatch_service
    admin_marker = f"user:{uuid.uuid4()}"

    assignment = await dispatch_service.dispatch_resource(
        incident_id=incident.id, resource_id=resource.id, assigned_by=admin_marker
    )

    assert assignment.assigned_by == admin_marker


@pytest.mark.asyncio
async def test_dispatch_resource_persists_and_is_queryable(client: AsyncClient, db_session) -> None:
    """The written row must actually be committed/visible, not just held on
    the DispatchService's own session — a fresh query should see it."""
    from sqlalchemy import select

    from app.db.models.resource_assignment import ResourceAssignment
    from app.main import app

    incident, resource = await _make_incident_and_resource(db_session)
    dispatch_service: DispatchService = app.state.container.dispatch_service

    assignment = await dispatch_service.dispatch_resource(
        incident_id=incident.id, resource_id=resource.id
    )

    result = await db_session.execute(
        select(ResourceAssignment).where(ResourceAssignment.id == assignment.id)
    )
    fetched = result.scalar_one()
    assert fetched.incident_id == incident.id
    assert fetched.resource_id == resource.id


@pytest.mark.asyncio
async def test_dispatch_resource_unknown_incident_raises(client: AsyncClient, db_session) -> None:
    """A resource_id/incident_id that doesn't exist violates the FK
    constraint rather than silently succeeding."""
    from sqlalchemy.exc import IntegrityError

    from app.main import app

    _, resource = await _make_incident_and_resource(db_session)
    dispatch_service: DispatchService = app.state.container.dispatch_service

    with pytest.raises(IntegrityError):
        await dispatch_service.dispatch_resource(incident_id=uuid.uuid4(), resource_id=resource.id)
