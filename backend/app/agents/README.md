# agents/

The AI Agent Framework & Orchestration Layer (Module 3). This package is
infrastructure only — it contains **zero** business logic, prompts, or
scoring rules for any specific agent.

| File | Responsibility |
|---|---|
| `base.py` | `BaseAgent` — abstract lifecycle (validate → retry+timeout execute → validate → metrics) every concrete agent inherits. |
| `types.py` | Shared types: `AgentRequest`/`AgentResponse`/`AgentContext`/`AgentMemory`, `NegotiationMessage`, `ConsensusDecision`, `TaskResult`, `StructuredOutput`. |
| `exceptions.py` | Agent-specific errors, subclassing `app.core.exceptions.StadiumPulseError`. |
| `registry.py` | `AgentRegistry` — register/discover agents, capabilities, health status. |
| `orchestrator.py` | `AgentOrchestrator` — executes a `Workflow` (staged, sequential today) against the registry. |
| `negotiation.py` | `NegotiationEngine`/`NegotiationSession` — proposal → challenge → rebuttal → vote → resolution state machine. `HighestConfidenceStrategy` is a placeholder consensus rule, not the product's real strategy. |
| `context.py` | `SharedContextManager` — per-workflow-run `AgentContext` + scratch memory. |
| `output.py` | `StructuredOutputEngine` — JSON parsing/recovery, schema validation, confidence extraction. |
| `memory.py` | `MemoryInterface`/`InMemoryMemoryStore`/`MemoryProvider` — memory abstractions only. Tournament Memory (pgvector-backed, embedding generation, similarity search) is a **future module**. |
| `prompts.py` | `PromptTemplate`/`PromptRegistry` — versioned, variable-validated prompt templates. |
| `observability.py` | `AgentMetricsRegistry` — per-agent execution metrics and traces. |

The multi-provider LLM layer (`AnthropicLLMClient`, `OpenAILLMClient`,
`GeminiLLMClient`, the rate-limiting wrapper, and the `build_llm_client`
factory) lives in `app/core/llm_client.py` / `app/core/llm_providers.py`,
not here — per ADR-0003, it's shared infrastructure many non-agent
callers may eventually need too, so it stays in `core/`.

## How a future agent module plugs in

```python
from app.agents.base import BaseAgent
from app.agents.types import AgentContext, AgentRequest, StructuredOutput

class IncidentAnalysisAgent(BaseAgent):
    agent_id = "incident_analysis"
    name = "Incident Analysis Agent"
    description = "Extracts structured incident data from raw reporter text."
    system_prompt = "..."
    supported_tasks = ("analyze_incident",)

    async def _execute(self, request: AgentRequest, context: AgentContext | None) -> StructuredOutput:
        # Real prompting/LLM-calling/business logic goes here.
        ...
```

Then, at that module's own startup wiring (not in `core/container.py`):

```python
container.agent_registry.register(IncidentAnalysisAgent())
```

Every agent module must depend only on `app.core.llm_client.LLMClient`
(the interface), never on a concrete provider class, so agents remain
unit-testable with a fake client and swappable if the underlying
provider ever changes.
