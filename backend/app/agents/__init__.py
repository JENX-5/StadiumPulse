"""
AI Agent Framework & Orchestration Layer (Module 3).

This package is the reusable infrastructure every concrete agent
(Predictive Intelligence, Incident Analysis, Resource Coordination,
Operational Consensus, Tournament Memory — each a future module) is built
against. It intentionally contains no agent-specific business logic.
"""

from app.agents.base import BaseAgent
from app.agents.context import SharedContextManager
from app.agents.exceptions import (
    AgentError,
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
    AgentValidationError,
    NegotiationError,
    PromptNotFoundError,
    StructuredOutputParseError,
)
from app.agents.memory import InMemoryMemoryStore, MemoryInterface, MemoryProvider
from app.agents.negotiation import (
    ConsensusStrategy,
    HighestConfidenceStrategy,
    NegotiationEngine,
    NegotiationSession,
)
from app.agents.orchestrator import AgentOrchestrator, Workflow, WorkflowResult, WorkflowStep
from app.agents.output import StructuredOutputEngine
from app.agents.prompts import PromptRegistry, PromptTemplate
from app.agents.registry import AgentRegistry
from app.agents.types import (
    AgentContext,
    AgentMemory,
    AgentRequest,
    AgentResponse,
    AgentTaskStatus,
    ConsensusDecision,
    ConsensusOutcome,
    NegotiationMessage,
    NegotiationMessageType,
    StructuredOutput,
    TaskResult,
)

__all__ = [
    "AgentContext",
    "AgentError",
    "AgentExecutionError",
    "AgentMemory",
    "AgentNotFoundError",
    "AgentOrchestrator",
    "AgentRegistry",
    "AgentRequest",
    "AgentResponse",
    "AgentTaskStatus",
    "AgentTimeoutError",
    "AgentValidationError",
    "BaseAgent",
    "ConsensusDecision",
    "ConsensusOutcome",
    "ConsensusStrategy",
    "HighestConfidenceStrategy",
    "InMemoryMemoryStore",
    "MemoryInterface",
    "MemoryProvider",
    "NegotiationEngine",
    "NegotiationError",
    "NegotiationMessage",
    "NegotiationMessageType",
    "NegotiationSession",
    "PromptNotFoundError",
    "PromptRegistry",
    "PromptTemplate",
    "SharedContextManager",
    "StructuredOutput",
    "StructuredOutputEngine",
    "StructuredOutputParseError",
    "TaskResult",
    "Workflow",
    "WorkflowResult",
    "WorkflowStep",
]
