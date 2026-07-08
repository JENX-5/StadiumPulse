"""
Centralized error handling.

Every domain error in the system should subclass `StadiumPulseError` so
`register_exception_handlers` can translate it into a single consistent
JSON error envelope. Individual modules (agents, API routers, services)
raise these instead of ad-hoc HTTPException calls, keeping error shape
uniform for the frontend regardless of which layer raised it.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class StadiumPulseError(Exception):
    """Base class for all domain errors raised anywhere in the application."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationFailedError(StadiumPulseError):
    """Raised when input fails domain-level validation beyond schema checks."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_failed"


class NotFoundError(StadiumPulseError):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class UnauthorizedError(StadiumPulseError):
    """Raised when authentication is missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class ForbiddenError(StadiumPulseError):
    """Raised when an authenticated user lacks permission for the action.

    Used for both role-based checks and ownership checks (e.g. a volunteer
    attempting to update a resource record that is not their own).
    """

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class LLMClientError(StadiumPulseError):
    """Raised when an LLM call fails after retries, before fallback is applied.

    Agent modules catch this to trigger their documented rule-based fallback
    rather than letting a raw provider error reach the API layer.
    """

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "llm_unavailable"


class DependencyUnavailableError(StadiumPulseError):
    """Raised when a required infrastructure dependency (DB, Redis) is down."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "dependency_unavailable"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a single, consistent JSON error envelope for every raised error."""

    @app.exception_handler(StadiumPulseError)
    async def handle_domain_error(request: Request, exc: StadiumPulseError) -> JSONResponse:
        logger.warning(
            "domain_error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internals (stack traces, driver errors) to the client.
        # Full detail goes to structured logs only.
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
        )
