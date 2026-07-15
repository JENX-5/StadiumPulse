"""Integration tests for the incident API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_incidents_empty(client: AsyncClient, db_session) -> None:
    """Test getting incidents when none exist."""
    import uuid
    from app.db.models.venue import Venue
    
    dummy_venue_id = uuid.uuid4()
    venue = Venue(id=dummy_venue_id, name="Test Venue", timezone="UTC")
    db_session.add(venue)
    await db_session.commit()
    
    response = await client.get(f"/api/v1/incidents/venue/{dummy_venue_id}")
    
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_incident(client: AsyncClient, db_session) -> None:
    """Test creating an incident and retrieving it."""
    import uuid
    from app.db.models.venue import Venue
    
    dummy_venue_id = uuid.uuid4()
    venue = Venue(id=dummy_venue_id, name="Test Venue", timezone="UTC")
    db_session.add(venue)
    await db_session.commit()
    
    # Create incident
    create_payload = {
        "venue_id": str(dummy_venue_id),
        "raw_text": "Spill reported in concourse",
        "severity": "medium",
        "source": "simulation",
    }
    create_response = await client.post("/api/v1/incidents/", json=create_payload)
    
    assert create_response.status_code == 201
    created_incident = create_response.json()
    assert created_incident["raw_text"] == "Spill reported in concourse"
    assert created_incident["venue_id"] == str(dummy_venue_id)
    assert created_incident["status"] == "open"
    
    # Retrieve incidents
    get_response = await client.get(f"/api/v1/incidents/venue/{dummy_venue_id}")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) > 0
    assert any(i["id"] == created_incident["id"] for i in incidents)

@pytest.mark.asyncio
async def test_update_incident_status(client: AsyncClient, db_session) -> None:
    """Test updating an incident status to resolved."""
    import uuid
    from app.db.models.venue import Venue
    
    dummy_venue_id = uuid.uuid4()
    venue = Venue(id=dummy_venue_id, name="Test Venue", timezone="UTC")
    db_session.add(venue)
    await db_session.commit()
    
    create_payload = {
        "venue_id": str(dummy_venue_id),
        "raw_text": "Medical issue",
        "severity": "high",
        "source": "simulation",
    }
    create_response = await client.post("/api/v1/incidents/", json=create_payload)
    assert create_response.status_code == 201
    incident_id = create_response.json()["id"]
    
    update_response = await client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "resolved"})
    assert update_response.status_code == 200
    
    updated_incident = update_response.json()
    assert updated_incident["id"] == incident_id
    assert updated_incident["status"] == "resolved"
