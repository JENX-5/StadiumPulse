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
    <Card className="flex flex-col h-full bg-card/40 backdrop-blur border-border/40 overflow-hidden shadow-xl">
      <CardHeader className="py-3 px-4 border-b border-border/40 bg-card/60">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 uppercase tracking-widest text-muted-foreground">
            <AlertCircle className="h-4 w-4" />
            Active Incidents
          </CardTitle>
          <Badge variant="secondary" className="rounded-full px-2 py-0.5 text-[10px]">
            {incidents.length}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-md bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : incidents.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground flex flex-col items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              </div>
              Monitoring for incidents...
            </div>
          ) : (
            <div className="flex flex-col">
              {incidents.map((incident) => (
                <div
                  key={incident.id}
                  className="p-3 border-b border-border/20 hover:bg-secondary/40 transition-colors cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-1.5">
                    <span className="text-sm font-medium leading-none group-hover:text-primary transition-colors">
                      {incident.raw_text.length > 50 ? incident.raw_text.substring(0, 50) + "…" : incident.raw_text}
                    </span>
                    <Badge variant="outline" className={`text-[9px] uppercase font-bold tracking-wider rounded-sm px-1.5 border ${getSeverityColor(incident.severity)}`}>
                      {incident.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
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
