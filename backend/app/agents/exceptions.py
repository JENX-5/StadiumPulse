"""
Agent-specific errors.

All subclass `StadiumPulseError` (app.core.exceptions) so they flow through
the same centralized JSON error envelope as every other domain error in the
system — an agent failure surfaced through the API looks like any other
error to the frontend, just with a different `error_code`.
"""

from __future__ import annotations

from fastapi import status

from app.core.exceptions import StadiumPulseError


class AgentError(StadiumPulseError):
    """Base class for every error raised by the agent framework."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "agent_error"


class AgentNotFoundError(AgentError):
    """Raised when the registry or orchestrator is asked for an unknown agent_id."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "agent_not_found"


class AgentValidationError(AgentError):
    """Raised when an `AgentRequest` or an agent's output fails validation."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "agent_validation_failed"


class AgentExecutionError(AgentError):
    """Raised when an agent's `_execute` raises after all retries are exhausted."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "agent_execution_failed"


class AgentTimeoutError(AgentError):
    """Raised when an agent's execution exceeds its configured timeout."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "agent_timeout"


class StructuredOutputParseError(AgentError):
    """Raised when the Structured Output Engine cannot recover a valid payload."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "structured_output_parse_failed"


class NegotiationError(AgentError):
    """Raised for invalid negotiation-session operations (e.g. out-of-order phases)."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "negotiation_error"


class PromptNotFoundError(AgentError):
    """Raised when the Prompt Registry is asked for an unknown template/version."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "prompt_not_found"
