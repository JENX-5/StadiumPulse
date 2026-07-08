# ADR 0004: Risk Score Current-Value Cache in Redis, History in Postgres

**Status:** Accepted
**Date:** 2026-07-08

## Context
`risk_scores` is a time-series table read very frequently by the Risk
Heatmap — every zone, every few seconds, per connected client. Hitting
Postgres directly on every heatmap poll does not scale gracefully at demo
concurrency and adds latency the UI doesn't need to pay.

## Decision
The **current** score per zone is cached in Redis (`zone:{zone_id}:risk`)
by the deterministic scorer on every tick. The `risk_scores` Postgres table
is write-through, used for **history and audit only** — trend charts, the
Explainability Drawer, and the Tournament Memory Agent's pattern matching
read from Postgres; the live heatmap reads from Redis.

## Consequences
- The heatmap's hot path never touches Postgres.
- `risk_scores` retains its full audit trail (`contributing_factors`,
  `narrative`) without being on the read-critical path.
- The scorer module (a future module) is responsible for the Redis
  write-through; this schema module only guarantees the Postgres side is
  indexed correctly for history queries (`ix_risk_scores_zone_computed_at`).
