import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { incidentsApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";

export function IncidentPanel() {
  const { venueId } = useAppStore();

  const { data: incidents = [], isLoading } = useQuery({
    queryKey: ["incidents", venueId],
    queryFn: () => incidentsApi.listByVenue(venueId),
  });

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
        return "bg-destructive text-destructive-foreground";
      case "HIGH":
        return "bg-orange-500/20 text-orange-500 border-orange-500/50";
      case "MEDIUM":
        return "bg-yellow-500/20 text-yellow-500 border-yellow-500/50";
      default:
        return "bg-secondary text-secondary-foreground";
    }
  };

  return (
    <Card className="flex h-full flex-col overflow-hidden border-border/60 bg-white/90 shadow-sm backdrop-blur dark:bg-card/90">
      <CardHeader className="border-b border-border/50 bg-muted/20 px-4 py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground">
            <AlertCircle className="h-4 w-4" />
            Active Incidents
          </CardTitle>
          <Badge variant="secondary" className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em]">
            {incidents.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-xl bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : incidents.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-8 text-center text-sm text-muted-foreground">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              </div>
              Monitoring for incidents...
            </div>
          ) : (
            <div className="flex flex-col">
              {incidents.map((incident) => (
                <div
                  key={incident.id}
                  className="group cursor-pointer border-b border-border/20 px-3 py-3 transition-colors hover:bg-muted/40"
                >
                  <div className="mb-1.5 flex items-start justify-between gap-2">
                    <span className="line-clamp-2 text-sm font-medium leading-snug group-hover:text-primary transition-colors">
                      {incident.raw_text.length > 50 ? incident.raw_text.substring(0, 50) + "…" : incident.raw_text}
                    </span>
                    <Badge variant="outline" className={`rounded-full border px-1.5 py-0 text-[9px] font-bold uppercase tracking-[0.18em] ${getSeverityColor(incident.severity)}`}>
                      {incident.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
                    <span className="truncate pr-4">{incident.raw_text}</span>
                    <span className="shrink-0">{new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
