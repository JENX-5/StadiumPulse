import { apiRequest } from "@/lib/api-client";
import { IncidentResponse, OperationalState, SimulationControl, SimulationStatusResponse } from "@/types/api";

export const incidentsApi = {
  listByVenue: (venueId: string) => 
    apiRequest<IncidentResponse[]>(`/api/v1/incidents/venue/${venueId}`),
    
  get: (incidentId: string) => 
    apiRequest<IncidentResponse>(`/api/v1/incidents/${incidentId}`),
};

export const stateApi = {
  getLiveState: (venueId: string) => 
    apiRequest<OperationalState>(`/api/v1/state/${venueId}`),
};

export const simulationApi = {
  getStatus: () => 
    apiRequest<SimulationStatusResponse>("/api/v1/simulation/status"),
    
  control: (payload: SimulationControl) => 
    apiRequest<SimulationStatusResponse>("/api/v1/simulation/control", {
      method: "POST",
      body: payload,
    }),
};
