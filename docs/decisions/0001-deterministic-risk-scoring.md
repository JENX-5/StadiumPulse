# ADR 0001: Deterministic Risk Scoring, LLM for Narrative Only

**Status:** Accepted
**Date:** 2026-07-08

## Context
The original architecture recomputed each zone's risk score via a
continuous LLM call on a rolling polling basis. This was identified as the
single largest cost and latency risk in the system during pre-implementation
review (Phase 1/2/8) — an LLM call is unnecessary for a computation that is
fundamentally a weighted function over density, velocity, and
historical-pattern-match.

## Decision
Split the Predictive Intelligence Agent into two layers:
1. A **deterministic scorer** (plain weighted function, no LLM) runs on
   every tick.
2. The **LLM is invoked only** to generate the human-readable narrative,
   and only when the score crosses a threshold or the zone's rank changes.

## Consequences
- ~70–90% fewer LLM calls across a full demo run, with no visible UX change.
- The deterministic scorer is simpler to implement and test than the
  polling LLM loop it replaces (net less code).
- The scorer's weights become a tunable, versioned artifact independent of
  prompt engineering — future model changes can't silently shift risk
  thresholds.
