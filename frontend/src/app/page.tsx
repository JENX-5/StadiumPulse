/**
 * Foundation placeholder landing page.
 *
 * The real Command Center Dashboard, Risk Heatmap, and other screens are
 * built in their own future frontend modules per the module-by-module
 * implementation plan. This page exists only to prove the build/dev
 * pipeline works end-to-end.
 */

"use client";

import { useEffect } from "react";

import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { IncidentPanel } from "@/components/dashboard/IncidentPanel";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StadiumMap } from "@/components/map/StadiumMap";
import { KPICards } from "@/components/metrics/KPICards";
import { SimulationControlPanel } from "@/components/simulation/SimulationControlPanel";
import { MissionTimeline } from "@/components/timeline/MissionTimeline";
import { stateApi } from "@/services/api";
import { connectWebSocket, disconnectWebSocket } from "@/services/websocket";
import { useAppStore } from "@/store/useAppStore";

export default function Home() {
  const { venueId, updateLiveState } = useAppStore();

  useEffect(() => {
    // 1. Fetch the initial hot-cache state from Redis
    stateApi
      .getLiveState(venueId)
      .then((state) => {
        updateLiveState(state);
      })
      .catch((err) => console.error("Failed to fetch initial state:", err));

    // 2. Open WebSocket connection for real-time telemetry (Simulation Engine ticks, etc)
    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [venueId, updateLiveState]);

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full w-full">
        {/* Top Split: Map & Side Panels */}
        <div className="flex flex-1 overflow-hidden p-3 lg:p-5 gap-3 lg:gap-5">
          {/* Left Area (KPIs & Map) */}
          <div className="flex-1 flex flex-col min-w-0">
            <KPICards />
            <div className="flex-1 min-h-0">
              <StadiumMap />
            </div>
          </div>

          {/* Right Area (Simulation Controls, AI Insights & Incidents List) */}
          <div className="w-80 xl:w-96 flex flex-col gap-3 lg:gap-5 shrink-0">
            <div className="shrink-0">
              <SimulationControlPanel />
            </div>
            <div className="shrink-0">
              <AIInsightsPanel />
            </div>
            <div className="flex-1 min-h-0">
              <IncidentPanel />
            </div>
          </div>
        </div>

        {/* Bottom Area: Real-time Mission Timeline */}
        <MissionTimeline />
      </div>
    </DashboardLayout>
  );
}
