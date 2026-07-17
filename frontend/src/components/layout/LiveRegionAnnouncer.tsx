"use client";

import { useAppStore } from "@/store/useAppStore";

/** Turns a raw timeline event type into a short, human-readable announcement.
 * Routine telemetry ticks are intentionally not announced -- a screen reader
 * user needs to hear about a new incident, not every 5-second crowd-density
 * tick. */
function describeEvent(type: string): string | null {
  const lower = type.toLowerCase();
  if (lower.includes("incident")) return "New incident reported.";
  if (lower.includes("alert")) return "New alert.";
  if (lower.includes("resource") && lower.includes("assign")) return "Resource assignment updated.";
  return null;
}

/**
 * A visually-hidden `aria-live` region that announces real-time operational
 * events (new incidents, alerts) to screen reader users. Without this, the
 * dashboard's entire premise -- real-time awareness -- is invisible to
 * anyone not looking directly at the screen when an update streams in over
 * the WebSocket (see services/websocket.ts).
 */
export function LiveRegionAnnouncer() {
  const latestEvent = useAppStore((state) => state.timelineEvents[0]);
  const message = latestEvent ? describeEvent(latestEvent.type) : null;

  return (
    <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
      {message}
    </div>
  );
}
