"""
Application entrypoint.

Builds the DI container once on startup (fail-fast on bad DB/Redis config),
attaches it to `app.state`, registers centralized exception handling,
CORS, and the v1 API router. This file intentionally contains no business
logic — it is composition only.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.websockets.router import router as ws_router
from app.core.config import get_settings
from app.core.container import build_container
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings)
logger: structlog.stdlib.BoundLogger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("application_starting", env=settings.env)
    app.state.container = await build_container(settings)
    try:
        yield
    finally:
        logger.info("application_shutting_down")
        await app.state.container.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="StadiumPulse API",
        description="Event-driven, multi-agent stadium operations platform.",
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(ws_router)

    # Unprefixed liveness probe for container orchestrators that expect
    # a bare `/health` regardless of API versioning.
    from app.api.v1.health import liveness

    app.get("/health", tags=["health"])(liveness)

    return app


app = create_app()
