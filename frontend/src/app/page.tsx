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

import { CommandCenterDashboard } from "@/components/dashboard/CommandCenterDashboard";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { AgentsView } from "@/components/views/AgentsView";
import { IncidentsView } from "@/components/views/IncidentsView";
import { ResourcesView } from "@/components/views/ResourcesView";
import { TimelineView } from "@/components/views/TimelineView";
import { stateApi } from "@/services/api";
import { connectWebSocket, disconnectWebSocket } from "@/services/websocket";
import { useAppStore } from "@/store/useAppStore";

export default function Home() {
  const venueId = useAppStore((state) => state.venueId);
  const activeView = useAppStore((state) => state.activeView);
  const updateLiveState = useAppStore((state) => state.updateLiveState);

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
        return <CommandCenterDashboard />;
    }
  };

  return (
    <DashboardLayout>
      <main className="h-full w-full">
        {renderContent()}
      </main>
    </DashboardLayout>
  );
}
