# Contributing to StadiumPulse

## Development workflow
1. `docker compose up --build` for the full local stack, or run backend/
   frontend independently per the README's "Local development" section.
2. Backend: `pytest tests/ -v` must pass; `ruff check .` and `black --check .`
   for style.
3. Frontend: `npm run type-check` and `npm run build` must pass.

## Module boundaries
- Agent modules depend only on `app.core.llm_client.LLMClient` (the
  interface), never a concrete provider client.
- Only Dispatch Service writes `resource_assignments` rows — see
  [`docs/decisions/0002`](./docs/decisions/0002-agent-ownership-boundary.md).
- New domain errors subclass `StadiumPulseError` in `app/core/exceptions.py`
  rather than raising `HTTPException` directly, to keep the error envelope
  consistent for the frontend.

## Commit style
Keep commits scoped to one module/concern. Reference the relevant ADR in
`docs/decisions/` when a commit implements or deviates from a recorded
decision.
