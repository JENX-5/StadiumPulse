# ADR 0005: Agent Framework Architecture (Module 3)

**Status:** Accepted
**Date:** 2026-07-08

## Context
Five distinct agents (Predictive Intelligence, Incident Analysis, Resource
Coordination, Operational Consensus, Tournament Memory) are planned across
future modules. Without a shared framework, each would duplicate its own
retry/timeout/validation/logging logic, its own ad-hoc negotiation
handling, and its own LLM provider coupling — exactly the kind of drift
ADR-0003 already flagged as a risk for the LLM client specifically.

## Decisions

1. **`BaseAgent` owns the lifecycle, not the reasoning.** Every concrete
   agent implements only `_execute()`. Validation, retry, timeout,
   confidence handling, metrics, and logging are inherited and not meant
   to be overridden except in unusual cases. This is Module 3's core bet:
   fixing bugs or changing retry policy in one place fixes it for every
   agent that will ever exist.

2. **The orchestrator only knows about `agent_id` strings, never concrete
   classes.** `AgentOrchestrator` resolves every step through
   `AgentRegistry.get(agent_id)`. A future agent module registers itself
   at its own startup wiring (`container.agent_registry.register(...)`) —
   `core/container.py` never imports a concrete agent.

3. **Workflows are staged, not flat, even though only sequential execution
   is implemented today.** `Workflow.stages: list[list[WorkflowStep]]`
   groups steps that *could* run in parallel once that's needed, without
   a breaking change to the `Workflow` shape or any caller — see
   `orchestrator.py`'s `_run_stage` docstring.

4. **Negotiation framework ships with a placeholder consensus strategy.**
   `HighestConfidenceStrategy` exists only so `NegotiationEngine` is
   exercisable and testable end-to-end today. The `ConsensusStrategy`
   protocol is the seam the Operational Consensus Agent's real strategy
   (weighing genuine multi-agent disagreement) will implement in a later
   module — this is explicitly called out in Module 3's scope as "no
   negotiation strategies yet."

5. **Multi-provider LLM layer stays in `core/`, not `agents/`, per
   ADR-0003 — extended, not replaced.** `app/core/llm_providers.py` adds
   `OpenAILLMClient`, `GeminiLLMClient`, a `RateLimitedLLMClient` wrapper,
   and the `build_llm_client(settings)` factory, all implementing/wrapping
   the existing `LLMClient` interface from `llm_client.py`. `Container`
   now calls the factory instead of hardcoding `AnthropicLLMClient`;
   nothing else changes for existing callers.

6. **Memory framework is interface-only.** `MemoryInterface` +
   `InMemoryMemoryStore` let the orchestrator/negotiation code be built
   and tested against a real (if non-persistent) implementation now.
   `TournamentMemory` (the pgvector-backed table from Module 2) still has
   no agent reading or writing it — that agent is a future module.

## Consequences
- Every future agent module's diff should mostly be `_execute()` plus a
  task-specific input/output schema — not another copy of retry/timeout
  boilerplate.
- Switching the default LLM provider (e.g. Anthropic → OpenAI for a
  specific environment) is a config change (`LLM_PROVIDER` env var), not
  a code change, anywhere in the codebase.
- The negotiation and orchestration data models (`NegotiationMessage`,
  `TaskResult`, etc.) are now fixed contracts; changing them once real
  agents depend on them is a breaking change across every agent module,
  so schema changes here should be treated with the same care as a DB
  migration.

## Not yet done (explicitly out of scope per Module 3)
- No concrete agents, prompts, or scoring logic.
- No real negotiation/consensus strategy.
- No Tournament Memory embedding generation or similarity search.
- No local-model provider implementation (`LocalLLMClient` is a stub that
  raises `NotImplementedError`).
