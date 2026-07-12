import { apiRequest } from "@/lib/api-client";
import { IncidentResponse, OperationalState, SimulationControl, SimulationStatusResponse } from "@/types/api";

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
