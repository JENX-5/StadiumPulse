import { apiRequest } from "@/lib/api-client";
import { 
  IncidentCreate, IncidentResponse, IncidentUpdate, OperationalState, SimulationControl, SimulationStatusResponse,
  Resource, TournamentMemory, ZoneResponse, ZoneRiskResponse 
} from "@/types/api";
import { AuthUser } from "@/store/useAuthStore";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  // Backend route is a strict OAuth2 password-grant endpoint
  // (`OAuth2PasswordRequestForm`), so this must be form-urlencoded with
  // `username`/`password` keys, not JSON.
  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/auth/token", {
      method: "POST",
      form: true,
      body: new URLSearchParams({ username: email, password }).toString(),
    }),

  me: () => apiRequest<AuthUser>("/auth/me"),
};

export const incidentsApi = {
  listByVenue: (venueId: string) => 
    apiRequest<IncidentResponse[]>(`/incidents/venue/${venueId}`),
    
  get: (incidentId: string) => 
    apiRequest<IncidentResponse>(`/incidents/${incidentId}`),

  create: (payload: IncidentCreate) =>
    apiRequest<IncidentResponse>("/incidents/", {
      method: "POST",
      body: payload,
    }),
    
  update: (incidentId: string, payload: IncidentUpdate) =>
    apiRequest<IncidentResponse>(`/incidents/${incidentId}`, {
      method: "PATCH",
      body: payload,
    }),
};

export const zonesApi = {
  list: (venueId: string) =>
    apiRequest<ZoneResponse[]>(`/zones/?venue_id=${venueId}`),
};

export const stateApi = {
  getLiveState: (venueId: string) => 
    apiRequest<OperationalState>(`/state/${venueId}`),
};

export const simulationApi = {
  getStatus: () => 
    apiRequest<SimulationStatusResponse>("/simulation/status"),
    
  control: (payload: SimulationControl) => 
    apiRequest<SimulationStatusResponse>("/simulation/control", {
      method: "POST",
      body: payload,
    }),
};

export const riskApi = {
  getHeatmap: (venueId: string) =>
    apiRequest<Record<string, number>>(`/risk/${venueId}/heatmap`),
    
  getZoneRisk: (venueId: string, zoneId: string) =>
    apiRequest<ZoneRiskResponse>(`/risk/${venueId}/zones/${zoneId}`),
};

export const memoryApi = {
  list: (venueId: string) =>
    apiRequest<TournamentMemory[]>(`/memory/?venue_id=${venueId}`),
};

export const resourcesApi = {
  list: (venueId: string) =>
    apiRequest<Resource[]>(`/resources?venue_id=${venueId}`),
    
  dispatch: (resourceId: string, incidentId: string) =>
    apiRequest<{ id: string; status: string; }>(`/resources/${resourceId}/dispatch`, {
      method: "POST",
      body: { incident_id: incidentId },
    }),
};
