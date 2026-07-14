"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Clock, Filter, Search } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { incidentsApi } from "@/services/api";
import { IncidentResponse } from "@/types/api";
import { useAppStore } from "@/store/useAppStore";

export function IncidentsView() {
  const { venueId } = useAppStore();
  const [filter, setFilter] = useState<"all" | "open" | "resolved">("all");
  const [search, setSearch] = useState("");
  const [selectedIncident, setSelectedIncident] = useState<IncidentResponse | null>(null);
  const queryClient = useQueryClient();

  const resolveMutation = useMutation({
    mutationFn: (id: string) => incidentsApi.update(id, { status: "resolved" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents", venueId] });
      setSelectedIncident(null);
    }
  });

  const { data: incidents = [], isLoading } = useQuery({
    queryKey: ["incidents", venueId],
    queryFn: () => incidentsApi.listByVenue(venueId),
    enabled: !!venueId,
  });

  const filtered = incidents.filter((i) => {
    const s = String(i.status).toLowerCase();
    if (filter === "open" && (s === "resolved" || s === "closed")) return false;
    if (filter === "resolved" && s !== "resolved" && s !== "closed") return false;
    if (search && !i.raw_text.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL": return "bg-muted text-foreground border-border";
      case "HIGH": return "bg-muted/80 text-muted-foreground border-border";
      case "MEDIUM": return "bg-muted/70 text-muted-foreground border-border";
      default: return "bg-secondary text-secondary-foreground";
    }
  };

  const getStatusIcon = (status: string) => {
    const s = String(status).toLowerCase();
    if (s === "resolved" || s === "closed") return <CheckCircle2 className="h-4 w-4 text-foreground" />;
    if (s === "in_progress") return <Clock className="h-4 w-4 text-muted-foreground" />;
    return <AlertCircle className="h-4 w-4 text-destructive" />;
  };

  return (
    <div className="flex flex-col h-full p-4 lg:p-6 gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Incidents</h1>
            <Badge variant="secondary" className="text-xs bg-muted text-foreground border-border">
          {incidents.filter((i) => String(i.status).toLowerCase() === "open" || String(i.status).toLowerCase() === "in_progress").length} Active
        </Badge>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search incidents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-border bg-background text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
          />
        </div>
        <div className="flex rounded-lg border border-border overflow-hidden">
          {(["all", "open", "resolved"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                filter === f
                  ? "bg-foreground text-background"
                  : "bg-background text-muted-foreground hover:bg-muted"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Incident list */}
      <ScrollArea className="flex-1 -mx-1" aria-live="polite" aria-atomic="false">
        {isLoading ? (
          <div className="space-y-3 px-1">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 rounded-lg bg-muted/20 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <AlertCircle className="h-8 w-8 mb-3 opacity-40" />
            <p className="text-sm">No incidents match your filter.</p>
          </div>
        ) : (
          <div className="space-y-2 px-1">
            {filtered.map((incident) => (
              <Card
                key={incident.id}
                className="bg-card/50 border-border/40 hover:bg-card/80 transition-all cursor-pointer group"
                onClick={() => setSelectedIncident(incident)}
              >
                <div className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{getStatusIcon(incident.status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium group-hover:text-primary transition-colors truncate">
                          {incident.raw_text.length > 80 ? incident.raw_text.substring(0, 80) + "…" : incident.raw_text}
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-[9px] uppercase font-bold tracking-wider rounded-sm px-1.5 ml-2 shrink-0 border ${getSeverityColor(incident.severity)}`}
                        >
                          {incident.severity.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                        <span>
                          {new Date(incident.created_at).toLocaleString([], {
                            month: "short", day: "numeric",
                            hour: "2-digit", minute: "2-digit",
                          })}
                        </span>
                        <Badge variant="outline" className="text-[9px] px-1.5 py-0 rounded-sm">
                          {String(incident.status).replace("_", " ")}
                        </Badge>
                        <span className="uppercase text-[9px] tracking-wider">{incident.source}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>

      <Dialog open={!!selectedIncident} onOpenChange={(open) => !open && setSelectedIncident(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Incident Details</DialogTitle>
          </DialogHeader>
          {selectedIncident && (
            <div className="space-y-4 pt-4">
              <div className="text-sm font-medium">
                {selectedIncident.raw_text}
              </div>
              <div className="flex gap-2">
                <Badge variant="outline" className={`text-xs uppercase tracking-wider ${getSeverityColor(selectedIncident.severity)}`}>
                  {selectedIncident.severity.toUpperCase()}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {String(selectedIncident.status).replace("_", " ")}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                Created: {new Date(selectedIncident.created_at).toLocaleString()}
                <br />
                Source: <span className="uppercase">{selectedIncident.source}</span>
              </div>
              
              <div className="flex justify-end pt-4">
                <Button 
                  onClick={() => resolveMutation.mutate(selectedIncident.id)}
                  disabled={String(selectedIncident.status).toLowerCase() === "resolved" || String(selectedIncident.status).toLowerCase() === "closed" || resolveMutation.isPending}
                >
                  {resolveMutation.isPending ? "Resolving..." : "Resolve Incident"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
