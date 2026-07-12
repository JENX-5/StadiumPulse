import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Clock, Shield, Users } from "lucide-react";

import { Card } from "@/components/ui/card";
import { incidentsApi, resourcesApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";

export function KPICards() {
  const { liveState, venueId } = useAppStore();

  const { data: incidents = [] } = useQuery({
    queryKey: ["incidents", venueId],
    queryFn: () => incidentsApi.listByVenue(venueId),
    enabled: !!venueId,
  });

  const { data: resources = [] } = useQuery({
    queryKey: ["resources", venueId],
    queryFn: () => resourcesApi.list(venueId),
    enabled: !!venueId,
  });

  const density = liveState?.global_crowd_density ?? 0.15;
  const activeIncidents = incidents.filter(
    (i) => i.status === "OPEN" || i.status === "IN_PROGRESS"
  ).length;
  const availableResources = resources.filter(
    (r) => r.status === "available"
  ).length;
  const totalResources = resources.length;

  // Compute avg time since open incidents were created (proxy for response time)
  const avgResponseMs =
    activeIncidents > 0
      ? incidents
          .filter((i) => i.status === "OPEN" || i.status === "IN_PROGRESS")
          .reduce((sum, i) => sum + (Date.now() - new Date(i.created_at).getTime()), 0) /
        activeIncidents
      : 0;
  const avgMinutes = Math.floor(avgResponseMs / 60000);
  const avgSeconds = Math.floor((avgResponseMs % 60000) / 1000);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 lg:gap-4 mb-4">
      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Active Incidents
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {activeIncidents}
        </div>
      </Card>

      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <Users className="h-4 w-4 text-primary" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Crowd Density
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {(density * 100).toFixed(1)}<span className="text-muted-foreground text-lg">%</span>
        </div>
      </Card>

      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <Shield className="h-4 w-4 text-emerald-500" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Resources
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {availableResources}<span className="text-muted-foreground text-lg">/{totalResources}</span>
        </div>
      </Card>

      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <Clock className="h-4 w-4 text-blue-500" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Avg Response
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {activeIncidents > 0 ? (
            <>
              {avgMinutes}<span className="text-muted-foreground text-sm">m</span>{" "}
              {avgSeconds}<span className="text-muted-foreground text-sm">s</span>
            </>
          ) : (
            <span className="text-muted-foreground text-lg">—</span>
          )}
        </div>
      </Card>
    </div>
  );
}
