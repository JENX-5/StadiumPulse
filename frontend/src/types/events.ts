/**
 * Shared event contract mirroring backend `app/core/events.py`.
 *
 * Kept as a hand-authored mirror rather than a codegen step at the
 * foundation stage (no OpenAPI schema exists yet to generate from). This
 * file should be revisited once the first real API module lands so the
 * two sides can't silently drift.
 */

export type EventSource = "simulation" | "live";

export interface StadiumPulseEvent<TPayload = Record<string, unknown>> {
  event_id: string;
  event_type: string;
  source: EventSource;
  occurred_at: string;
  venue_id: string;
  payload: TPayload;
}
