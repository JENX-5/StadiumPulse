"""Integration tests for the incident API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.db.models.user import UserRole


async def _make_venue(db_session) -> uuid.UUID:
    from app.db.models.venue import Venue

    venue_id = uuid.uuid4()
    db_session.add(Venue(id=venue_id, name="Test Venue", timezone="UTC"))
    await db_session.commit()
    return venue_id


@pytest.mark.asyncio
async def test_get_incidents_empty(client: AsyncClient, db_session, make_auth_headers) -> None:
    """Test getting incidents when none exist."""
    venue_id = await _make_venue(db_session)
    headers = await make_auth_headers(UserRole.FAN)

    response = await client.get(f"/api/v1/incidents/venue/{venue_id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_incident(client: AsyncClient, db_session, make_auth_headers) -> None:
    """Test creating an incident and retrieving it, including that the
    multi-agent pipeline actually populated a structured recommendation
    (this is the exact regression a task_type/input_data mismatch, or a
    silently-swallowed agent failure, would show up as)."""
    venue_id = await _make_venue(db_session)
    dispatcher_headers = await make_auth_headers(UserRole.DISPATCHER)

    create_payload = {
        "venue_id": str(venue_id),
        "raw_text": "Spill reported in concourse",
        "severity": "medium",
        "source": "simulation",
    }
    create_response = await client.post(
        "/api/v1/incidents/", json=create_payload, headers=dispatcher_headers
    )

    assert create_response.status_code == 201
    created_incident = create_response.json()
    assert created_incident["raw_text"] == "Spill reported in concourse"
    assert created_incident["venue_id"] == str(venue_id)
    assert created_incident["status"] == "open"

    # The Incident Analysis Agent must have run (LLM call or its
    # deterministic fallback) and populated a structured analysis.
    structured_summary = created_incident["structured_summary"]
    assert structured_summary is not None
    assert structured_summary["analysis"] is not None
    assert structured_summary["analysis"]["incident_type"]
    assert structured_summary["analysis"]["severity"]

    # Retrieve incidents
    get_response = await client.get(
        f"/api/v1/incidents/venue/{venue_id}", headers=dispatcher_headers
    )
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) > 0
    assert any(i["id"] == created_incident["id"] for i in incidents)


@pytest.mark.asyncio
async def test_create_incident_ranks_available_resources(
    client: AsyncClient, db_session, make_auth_headers
) -> None:
    """When resources are available in the venue, Resource Coordination and
    Operational Consensus must actually run and produce a recommendation --
    this is the pipeline stage that was previously wired with the wrong
    task_type/input_data and always failed silently."""
    from app.db.models.resource import Resource, ResourceStatus, ResourceType

    venue_id = await _make_venue(db_session)
    db_session.add(
        Resource(
            venue_id=venue_id,
            label="Medical Unit 1",
            resource_type=ResourceType.MEDICAL,
            status=ResourceStatus.AVAILABLE,
        )
    )
    await db_session.commit()

    dispatcher_headers = await make_auth_headers(UserRole.DISPATCHER)
    create_payload = {
        "venue_id": str(venue_id),
        "raw_text": "Person collapsed near section 114",
        "severity": "high",
        "source": "simulation",
    }
    create_response = await client.post(
        "/api/v1/incidents/", json=create_payload, headers=dispatcher_headers
    )
    assert create_response.status_code == 201
    structured_summary = create_response.json()["structured_summary"]

    assert structured_summary["recommended_resources"] is not None
    assert "ranked_resource_ids" in structured_summary["recommended_resources"]
    assert structured_summary["consensus"] is not None
    assert structured_summary["consensus"]["outcome"] in ("accepted", "no_consensus")

    # The negotiation transcript (Explainability Drawer) must be persisted.
    from sqlalchemy import select

    from app.db.models.negotiation import Negotiation

    result = await db_session.execute(
        select(Negotiation).where(
            Negotiation.incident_id == uuid.UUID(create_response.json()["id"])
        )
    )
    turns = result.scalars().all()
    assert len(turns) >= 2
    assert {t.phase.value for t in turns} == {"proposal", "resolution"}

    # Tournament Memory must have embedded and stored a memory for this incident.
    from app.db.models.tournament_memory import TournamentMemory

    memory_result = await db_session.execute(
        select(TournamentMemory).where(TournamentMemory.venue_id == venue_id)
    )
    memories = memory_result.scalars().all()
    assert len(memories) == 1
    assert len(memories[0].embedding) == 1024


@pytest.mark.asyncio
async def test_update_incident_status(client: AsyncClient, db_session, make_auth_headers) -> None:
    """Test updating an incident status to resolved."""
    venue_id = await _make_venue(db_session)
    dispatcher_headers = await make_auth_headers(UserRole.DISPATCHER)

    create_payload = {
        "venue_id": str(venue_id),
        "raw_text": "Medical issue",
        "severity": "high",
        "source": "simulation",
    }
    create_response = await client.post(
        "/api/v1/incidents/", json=create_payload, headers=dispatcher_headers
    )
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"status": "resolved"},
        headers=dispatcher_headers,
    )
    assert update_response.status_code == 200

    updated_incident = update_response.json()
    assert updated_incident["id"] == incident_id
    assert updated_incident["status"] == "resolved"


@pytest.mark.asyncio
async def test_create_incident_requires_authentication(client: AsyncClient, db_session) -> None:
    """Unauthenticated callers must be rejected -- incident creation both
    writes operational state and triggers real LLM calls."""
    venue_id = await _make_venue(db_session)

    response = await client.post(
        "/api/v1/incidents/",
        json={"venue_id": str(venue_id), "raw_text": "test", "source": "simulation"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_incident_requires_dispatcher_role(
    client: AsyncClient, db_session, make_auth_headers
) -> None:
    """A merely-authenticated fan must not be able to create incidents --
    only dispatcher (or admin) accounts may."""
    venue_id = await _make_venue(db_session)
    fan_headers = await make_auth_headers(UserRole.FAN)

    response = await client.post(
        "/api/v1/incidents/",
        json={"venue_id": str(venue_id), "raw_text": "test", "source": "simulation"},
        headers=fan_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_incidents_requires_authentication(client: AsyncClient, db_session) -> None:
    venue_id = await _make_venue(db_session)

    response = await client.get(f"/api/v1/incidents/venue/{venue_id}")

    assert response.status_code == 401
