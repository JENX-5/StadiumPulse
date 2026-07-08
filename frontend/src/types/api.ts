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
  speed_multiplier?: number;
  deterministic?: boolean;
}

export interface SimulationStatusResponse {
  is_running: boolean;
  is_paused: boolean;
  speed_multiplier: number;
  deterministic: boolean;
}

export interface OperationalState {
  venue_id: string;
  active_incidents: number;
  global_crowd_density: number;
  global_noise_level: number;
  available_resources: number;
  [key: string]: any;
}
