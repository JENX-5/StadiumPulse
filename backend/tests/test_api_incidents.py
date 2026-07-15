"""Integration tests for the incident API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_incidents_empty(client: AsyncClient) -> None:
    """Test getting incidents when none exist."""
    # Assuming venue_id needs to be passed. We'll just pass a dummy UUID.
    dummy_venue_id = "12345678-1234-5678-1234-567812345678"
    response = await client.get(f"/api/v1/incidents/?venue_id={dummy_venue_id}")
    
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_incident(client: AsyncClient) -> None:
    """Test creating an incident and retrieving it."""
    dummy_venue_id = "12345678-1234-5678-1234-567812345678"
    
    # Create incident
    create_payload = {
        "venue_id": dummy_venue_id,
        "raw_text": "Spill reported in concourse",
        "severity": "medium",
        "source": "simulation",
    }
    create_response = await client.post("/api/v1/incidents/", json=create_payload)
    
    assert create_response.status_code == 201
    created_incident = create_response.json()
    assert created_incident["raw_text"] == "Spill reported in concourse"
    assert created_incident["venue_id"] == dummy_venue_id
    assert created_incident["status"] == "open"
    
    # Retrieve incidents
    get_response = await client.get(f"/api/v1/incidents/?venue_id={dummy_venue_id}")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) > 0
    assert any(i["id"] == created_incident["id"] for i in incidents)

@pytest.mark.asyncio
async def test_update_incident_status(client: AsyncClient) -> None:
    """Test updating an incident status to resolved."""
    dummy_venue_id = "12345678-1234-5678-1234-567812345678"
    
    create_payload = {
        "venue_id": dummy_venue_id,
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
