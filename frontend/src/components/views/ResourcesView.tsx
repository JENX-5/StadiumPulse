"use client";

import { useQuery } from "@tanstack/react-query";
import { HardHat, HeartPulse, Search, ShieldAlert, UserSquare2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { resourcesApi, zonesApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";

export function ResourcesView() {
  const { venueId } = useAppStore();
  const [filter, setFilter] = useState<"all" | "available" | "assigned" | "offline">("all");

  const { data: resources = [], isLoading } = useQuery({
    queryKey: ["resources", venueId],
    queryFn: () => resourcesApi.list(venueId),
    enabled: !!venueId,
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["zones", venueId],
    queryFn: () => zonesApi.list(venueId),
    enabled: !!venueId,
  });

  const zoneMap = new Map(zones.map((z) => [z.id, z.name]));

  const filtered = resources.filter((r) => {
    if (filter !== "all" && r.status.toLowerCase() !== filter) return false;
    return true;
  });

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "medical": return <HeartPulse className="h-4 w-4 text-foreground" />;
      case "security": return <ShieldAlert className="h-4 w-4 text-foreground" />;
      case "maintenance":
      case "cleaning": return <HardHat className="h-4 w-4 text-foreground" />;
      case "volunteer": return <UserSquare2 className="h-4 w-4 text-foreground" />;
      default: return <ShieldAlert className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "available": return "bg-muted text-foreground border-border";
      case "assigned":
      case "busy": return "bg-muted/70 text-muted-foreground border-border";
      case "offline": return "bg-muted text-muted-foreground border-border";
      default: return "bg-secondary text-secondary-foreground";
    }
  };

  const stats = {
    total: resources.length,
    available: resources.filter((r) => r.status.toLowerCase() === "available").length,
    assigned: resources.filter((r) => r.status.toLowerCase() === "assigned" || r.status.toLowerCase() === "busy").length,
    offline: resources.filter((r) => r.status.toLowerCase() === "offline").length,
  };

  return (
    <div className="flex flex-col h-full p-4 lg:p-6 gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Resources</h1>
        <div className="flex gap-2">
          <Badge className="bg-muted text-foreground border-border">{stats.available} Available</Badge>
          <Badge className="bg-muted/70 text-muted-foreground border-border">{stats.assigned} Active</Badge>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3">
        {(["all", "available", "assigned", "offline"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg border p-3 text-center transition-all ${
              filter === f
                ? "border-primary bg-primary/10 text-primary"
                : "border-border/40 bg-card/30 text-muted-foreground hover:bg-card/60"
            }`}
          >
            <div className="text-2xl font-semibold">
              {f === "all" ? stats.total : stats[f as keyof typeof stats]}
            </div>
            <div className="text-[10px] uppercase tracking-wider font-medium mt-1 capitalize">{f}</div>
          </button>
        ))}
      </div>

      {/* Resource list */}
      <ScrollArea className="flex-1 -mx-1">
        {isLoading ? (
          <div className="space-y-3 px-1">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 rounded-lg bg-muted/20 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <p className="text-sm">No resources match this filter.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 px-1">
            {filtered.map((resource) => (
              <Card
                key={resource.id}
                className="bg-card/50 border-border/40 hover:bg-card/80 transition-all p-4"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-muted/30 flex items-center justify-center">
                    {getTypeIcon(resource.resource_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{resource.label}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge
                        variant="outline"
                        className={`text-[9px] uppercase font-bold tracking-wider rounded-sm px-1.5 border ${getStatusColor(resource.status)}`}
                      >
                        {resource.status}
                      </Badge>
                      {resource.current_zone_id && (
                        <span className="text-[10px] text-muted-foreground truncate">
                          {zoneMap.get(resource.current_zone_id) ?? "Unknown zone"}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
