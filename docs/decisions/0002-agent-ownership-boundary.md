# ADR 0002: Resource Coordination Agent Proposes, Dispatch Service Executes

**Status:** Accepted
**Date:** 2026-07-08

## Context
Both the Resource Coordination Agent (RCA) and the Dispatch Service
"touch" resource assignment in the original spec, without a hard line
drawn between them. Left ambiguous, this risks duplicated or conflicting
write logic once multiple developers implement adjacent code in parallel.

## Decision
- The **Resource Coordination Agent** only proposes ranked candidates. It
  is pure reasoning: no database writes, no notifications, no side effects.
- The **Dispatch Service** is the only module permitted to write a
  `resource_assignments` row or trigger a notification.

## Consequences
- A single, unambiguous source of truth for "who actually assigned this
  resource" — critical for the audit trail the Explainability Drawer
  depends on.
- RCA becomes trivially unit-testable (pure function: roster + incident in,
  ranked list out) with no database or notification mocking required.
- Any future module that needs to trigger a dispatch must go through
  Dispatch Service's public interface, preventing bypass writes.
