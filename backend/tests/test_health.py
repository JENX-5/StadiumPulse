"""Integration tests for the liveness health endpoint.

Readiness (`/health/ready`) is intentionally not covered here — it requires
real Postgres/Redis connections and belongs in the integration test suite
introduced alongside the database module (Phase 10 recommendation: 3-4
end-to-end integration tests take priority over broad unit coverage).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_liveness_is_unprefixed(client: AsyncClient) -> None:
    """Liveness must be reachable without the /api/v1 prefix for orchestrators."""
    prefixed_response = await client.get("/api/v1/health")
    unprefixed_response = await client.get("/health")

    assert prefixed_response.status_code == 200
    assert unprefixed_response.status_code == 200
