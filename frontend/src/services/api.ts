import { apiRequest } from "@/lib/api-client";
import { 
  IncidentResponse, OperationalState, SimulationControl, SimulationStatusResponse,
  Resource, TournamentMemory, ZoneRiskResponse 
} from "@/types/api";

export const incidentsApi = {
  listByVenue: (venueId: string) => 
    apiRequest<IncidentResponse[]>(`/incidents/venue/${venueId}`),
    
  get: (incidentId: string) => 
    apiRequest<IncidentResponse>(`/incidents/${incidentId}`),
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
    apiRequest<TournamentMemory[]>(`/memory?venue_id=${venueId}`),
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
