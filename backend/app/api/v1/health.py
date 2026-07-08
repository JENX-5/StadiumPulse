"""
Health check endpoints.

`GET /health` is intentionally dependency-free (process liveness only) so
container orchestrators never flap the service on a transient DB blip.

`GET /health/ready` actually checks Postgres and Redis connectivity — this
is also the endpoint the team pings a few minutes before judging to warm
managed-provider free-tier connections (Phase 10, Third-party risk).
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.container import Container
from app.core.dependencies import get_container

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def liveness() -> dict[str, str]:
    """Process is up. No external dependency checks."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(
    container: Annotated[Container, Depends(get_container)],
) -> dict[str, object]:
    """Process is up AND its dependencies (Postgres, Redis) are reachable."""
    checks: dict[str, str] = {}

    try:
        async with container.db_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — deliberately broad for a health probe
        logger.error("readiness_db_check_failed", error=str(exc))
        checks["database"] = "unavailable"

    try:
        await container.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.error("readiness_redis_check_failed", error=str(exc))
        checks["redis"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
