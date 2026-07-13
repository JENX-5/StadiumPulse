/**
 * Main dashboard page.
 *
 * Uses the `activeView` from the Zustand store to switch between
 * different content views (Live Map, Incidents, Resources, AI Agents,
 * Timeline) without full-page navigation.
 *
 * The Live Map view uses resizable panels so users can drag to resize
 * the map vs. the right sidebar, and the main area vs. the bottom timeline.
 */

"use client";

import { useEffect } from "react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";

import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { IncidentPanel } from "@/components/dashboard/IncidentPanel";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StadiumMap } from "@/components/map/StadiumMap";
import { KPICards } from "@/components/metrics/KPICards";
import { SimulationControlPanel } from "@/components/simulation/SimulationControlPanel";
import { MissionTimeline } from "@/components/timeline/MissionTimeline";
import { AgentsView } from "@/components/views/AgentsView";
import { IncidentsView } from "@/components/views/IncidentsView";
import { ResourcesView } from "@/components/views/ResourcesView";
import { TimelineView } from "@/components/views/TimelineView";
import { stateApi } from "@/services/api";
import { connectWebSocket, disconnectWebSocket } from "@/services/websocket";
import { useAppStore } from "@/store/useAppStore";

function ResizeHandle({ direction = "horizontal" }: { direction?: "horizontal" | "vertical" }) {
  const isHorizontal = direction === "horizontal";
  return (
    <PanelResizeHandle
      className={`
        group relative flex items-center justify-center
        ${isHorizontal ? "w-2 cursor-col-resize" : "h-2 cursor-row-resize"}
        hover:bg-primary/10 active:bg-primary/20 transition-colors
      `}
    >
      <div
        className={`
          rounded-full bg-border/60 group-hover:bg-primary/50 group-active:bg-primary transition-colors
          ${isHorizontal ? "w-0.5 h-8" : "h-0.5 w-8"}
        `}
      />
    </PanelResizeHandle>
  );
}

export default function Home() {
  const { venueId, activeView, updateLiveState } = useAppStore();

  useEffect(() => {
    stateApi
      .getLiveState(venueId)
      .then((state) => {
        updateLiveState(state);
      })
      .catch((err) => console.warn("Failed to fetch initial state:", err));

    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [venueId, updateLiveState]);

  const renderContent = () => {
    switch (activeView) {
      case "incidents":
        return <IncidentsView />;
      case "resources":
        return <ResourcesView />;
      case "agents":
        return <AgentsView />;
      case "timeline":
        return <TimelineView />;
      case "map":
      default:
        return (
          <PanelGroup direction="vertical" className="h-full w-full">
            {/* Top area: Map + Side Panels */}
            <Panel defaultSize={78} minSize={40}>
              <PanelGroup direction="horizontal" className="h-full">
                {/* Left: KPIs & Map */}
                <Panel defaultSize={72} minSize={35}>
                  <div className="flex flex-col h-full p-3 lg:p-5 gap-3 lg:gap-5">
                    <KPICards />
                    <div className="flex-1 min-h-0">
                      <StadiumMap />
                    </div>
                  </div>
                </Panel>

                <ResizeHandle direction="horizontal" />

                {/* Right: Simulation Controls, AI Insights & Incidents */}
                <Panel defaultSize={28} minSize={18} maxSize={45}>
                  <div className="flex flex-col h-full gap-3 lg:gap-5 p-3 lg:p-5 pl-0 overflow-y-auto">
                    <SimulationControlPanel />
                    <AIInsightsPanel />
                    <div className="flex-1 min-h-0">
                      <IncidentPanel />
                    </div>
                  </div>
                </Panel>
              </PanelGroup>
            </Panel>

            <ResizeHandle direction="vertical" />

            {/* Bottom: Timeline */}
            <Panel defaultSize={22} minSize={8} maxSize={50}>
              <MissionTimeline />
            </Panel>
          </PanelGroup>
        );
    }
  };

  return (
    <DashboardLayout>
      {renderContent()}
    </DashboardLayout>
  );
}
