# ADR 0003: LLMClient Lives in core/, Not agents/

**Status:** Accepted
**Date:** 2026-07-08

## Context
Predictive Intelligence, Incident Analysis, Resource Coordination,
Operational Consensus, and Tournament Memory agents all depend on the same
underlying LLM call pattern (structured JSON output, retry-once-on-parse-
failure, timeout handling). Placing the client inside `agents/` risked it
becoming agent-specific rather than a shared dependency.

## Decision
`LLMClient` (interface) and `AnthropicLLMClient` (implementation) live in
`backend/app/core/llm_client.py`, exposed through the DI container
(`core/container.py`) and FastAPI dependency (`core/dependencies.py`).
Every agent type-hints against the `LLMClient` interface, never the
concrete Anthropic implementation.

## Consequences
- Single vendor lock-in risk (Anthropic/Claude for the entire reasoning
  layer) is mitigated: swapping providers means writing one new class, not
  touching five agents.
- Strict JSON schema validation + one corrective retry (Critical Fix #4)
  is implemented exactly once and inherited by every agent automatically.
- Agents become unit-testable with a fake `LLMClient` that returns
  canned responses, with no network calls in the test suite.
