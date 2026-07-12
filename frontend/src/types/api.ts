export interface IncidentResponse {
  id: string;
  venue_id: string;
  title: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  source: string;
  created_at: string;
  updated_at: string;
  raw_text: string;
}

export interface SimulationControl {
  command: "start" | "stop" | "pause" | "resume";
  venue_id?: string;
  speed_multiplier?: number;
  deterministic?: boolean;
  random_seed?: number;
}

export interface SimulationStatusResponse {
  is_running: boolean;
  is_paused: boolean;
  speed_multiplier: number;
  deterministic: boolean;
  venue_id: string | null;
}

export interface OperationalState {
  venue_id: string;
  active_incidents: number;
  global_crowd_density: number;
  global_noise_level: number;
  available_resources: number;
  [key: string]: any;
}

export interface Resource {
  id: string;
  label: string;
  resource_type: "medical" | "security" | "cleaning" | "volunteer" | "maintenance";
  status: "available" | "assigned" | "busy" | "offline";
  current_zone_id: string | null;
}

export interface TournamentMemory {
  id: string;
  summary: string;
  pattern_type: string;
  source_incident_ids: string[];
  created_at: string;
}

export interface ZoneRiskResponse {
  zone_id: string;
  risk_score: number;
  contributing_factors: Record<string, number>;
}

export interface ZoneResponse {
  id: string;
  venue_id: string;
  name: string;
  capacity: number | null;
}

export interface IncidentCreate {
  venue_id: string;
  zone_id?: string | null;
  raw_text: string;
  // Backend `IncidentSeverity` StrEnum values are lowercase (unlike
  // `IncidentResponse.severity`, which the API returns as-is from the same
  // lowercase enum — existing components upper-case it for display, e.g.
  // `IncidentPanel`'s `getSeverityColor`).
  severity: "critical" | "high" | "medium" | "low";
  source?: "simulation" | "live";
}
