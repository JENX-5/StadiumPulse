import { create } from "zustand";
import { OperationalState } from "@/types/api";

export interface TimelineEvent {
  id: string;
  type: string;
  timestamp: string;
  payload: any;
}

interface AppState {
  // Demo venue UUID from our backend seed
  venueId: string;
  activeZoneId: string | null;
  liveState: OperationalState | null;
  timelineEvents: TimelineEvent[];
  
  setVenueId: (id: string) => void;
  setActiveZoneId: (id: string | null) => void;
  updateLiveState: (state: Partial<OperationalState>) => void;
  addTimelineEvent: (event: TimelineEvent) => void;
}

export const useAppStore = create<AppState>((set) => ({
  venueId: "11111111-1111-1111-1111-111111111111", 
  activeZoneId: null,
  liveState: null,
  timelineEvents: [],
  
  setVenueId: (id) => set({ venueId: id }),
  setActiveZoneId: (id) => set({ activeZoneId: id }),
  updateLiveState: (update) => 
    set((state) => ({ 
      liveState: state.liveState ? { ...state.liveState, ...update } : update as OperationalState 
    })),
  addTimelineEvent: (event) => 
    set((state) => ({ 
      // Keep only the last 100 events to prevent memory bloat
      timelineEvents: [event, ...state.timelineEvents].slice(0, 100) 
    })),
}));
