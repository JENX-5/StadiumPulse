"""
Application entrypoint.

Builds the DI container once on startup (fail-fast on bad DB/Redis config),
attaches it to `app.state`, registers centralized exception handling,
CORS, and the v1 API router. This file intentionally contains no business
logic — it is composition only.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.api.websockets.router import router as ws_router
from app.core.config import Settings, get_settings
from app.core.container import build_container
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.services.event_broadcaster import run_event_bridge

logger: structlog.stdlib.BoundLogger = get_logger(__name__)


def _make_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("application_starting", env=settings.env)
        app.state.container = await build_container(settings)
        # Bridges Redis pub/sub (EventBus) to connected browser WebSocket
        # clients — see app/services/event_broadcaster.py for why this exists.
        bridge_task = asyncio.create_task(run_event_bridge(app.state.container.event_bus))
        try:
            yield
        finally:
            logger.info("application_shutting_down")
            bridge_task.cancel()
            await app.state.container.shutdown()

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. `settings` is injectable (rather than always
    reading the process-wide cached singleton) so tests can construct an
    app instance with different config -- e.g. rate limiting explicitly
    enabled -- without mutating global environment state."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="StadiumPulse API",
        description="Event-driven, multi-agent stadium operations platform.",
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        lifespan=_make_lifespan(settings),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # Per-client-IP HTTP rate limit, independent of the LLM-call budget
    # (RateLimitedLLMClient). Without this, an unauthenticated client could
    # hammer LLM-triggering endpoints (e.g. POST /incidents/) and both flood
    # the database and exhaust the shared LLM budget for every other user.
    # Disabled only in the test env: the ASGI test transport presents one
    # synthetic client address for the whole process, so a real test suite's
    # request volume would trip the same bucket real abusive traffic should.
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.http_rate_limit],
        enabled=settings.env != "test",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(ws_router)

    # Unprefixed liveness probe for container orchestrators that expect
    # a bare `/health` regardless of API versioning.
    from app.api.v1.health import liveness

    app.get("/health", tags=["health"])(liveness)

    return app


app = create_app()
