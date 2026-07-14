"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, AlertCircle, Bot, Clock3, Terminal } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TimelineEvent, useAppStore } from "@/store/useAppStore";

type FilterValue = "all" | "incident" | "agent" | "simulation" | "system";

function getCategory(type: string): FilterValue {
  if (type.includes("incident")) return "incident";
  if (type.includes("agent")) return "agent";
  if (type.includes("simulation")) return "simulation";
  return "system";
}

export function MissionTimeline() {
  const { timelineEvents } = useAppStore();
  const [filter, setFilter] = useState<FilterValue>("all");

  const filtered = useMemo(
    () => timelineEvents.filter((event) => filter === "all" || getCategory(event.type) === filter),
    [filter, timelineEvents]
  );

  const counts = useMemo(
    () => ({
      incident: timelineEvents.filter((event) => getCategory(event.type) === "incident").length,
      agent: timelineEvents.filter((event) => getCategory(event.type) === "agent").length,
      simulation: timelineEvents.filter((event) => getCategory(event.type) === "simulation").length,
      system: timelineEvents.filter((event) => getCategory(event.type) === "system").length,
    }),
    [timelineEvents]
  );

  const getEventIcon = (type: string) => {
    if (type.includes("incident")) return <AlertCircle className="h-3.5 w-3.5 text-foreground" />;
    if (type.includes("agent") || type.includes("simulation")) return <Bot className="h-3.5 w-3.5 text-foreground" />;
    return <Activity className="h-3.5 w-3.5 text-muted-foreground" />;
  };

  const getBadgeTone = (type: string) => {
    if (type.includes("incident")) return "border-border/60 bg-background text-foreground";
    if (type.includes("agent")) return "border-border/60 bg-muted text-foreground";
    if (type.includes("simulation")) return "border-border/60 bg-muted/70 text-muted-foreground";
    return "border-border/60 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200";
  };

  const formatPayload = (payload: any) => {
    if (!payload) return "";
    try {
      return JSON.stringify(payload).substring(0, 120) + (JSON.stringify(payload).length > 120 ? "..." : "");
    } catch {
      return String(payload);
    }
  };

  return (
    <Card className="flex h-full flex-col overflow-hidden border-0 bg-transparent shadow-none">
      <CardHeader className="border-b border-border/50 bg-background/70 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground">
              <Terminal className="h-4 w-4 text-foreground" />
              Live Operational Telemetry
            </CardTitle>
            <div className="text-[11px] text-muted-foreground">Streaming camera, AI, crowd, and resource events in real time.</div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {([
              { key: "all", label: "All", count: timelineEvents.length },
              { key: "incident", label: "Incidents", count: counts.incident },
              { key: "agent", label: "AI", count: counts.agent },
              { key: "simulation", label: "Simulation", count: counts.simulation },
              { key: "system", label: "System", count: counts.system },
            ] as const).map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setFilter(item.key)}
                className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] transition-colors ${
                  filter === item.key
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border/60 bg-background/70 text-muted-foreground hover:bg-muted"
                }`}
              >
                {item.label} <span className="ml-1 opacity-80">{item.count}</span>
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="min-h-0 flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="space-y-1 p-4">
            <AnimatePresence initial={false}>
              {filtered.map((event: TimelineEvent) => {
                const category = getCategory(event.type);
                return (
                  <motion.div
                    key={event.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    className="group grid grid-cols-[96px_160px_minmax(0,1fr)] items-start gap-3 rounded-xl border border-border/60 bg-white/80 px-3 py-3 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:bg-card/80"
                  >
                    <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
                      <Clock3 className="h-3.5 w-3.5 text-muted-foreground" />
                      {new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/50">{getEventIcon(event.type)}</span>
                      <div className="min-w-0">
                        <Badge variant="outline" className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] ${getBadgeTone(event.type)}`}>
                          {category}
                        </Badge>
                        <div className="mt-1 truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/80">{event.type}</div>
                      </div>
                    </div>

                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Payload</span>
                        <span className="h-px flex-1 bg-border/60" />
                      </div>
                      <p className="max-h-12 overflow-hidden text-sm leading-relaxed text-foreground/85">
                        {event.payload ? formatPayload(event.payload) : "Event received"}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {filtered.length === 0 && (
              <div className="flex min-h-[180px] items-center justify-center rounded-xl border border-dashed border-border/60 bg-muted/20 p-6 text-center text-sm text-muted-foreground">
                No events match the selected filter. Start or resume the simulation to generate telemetry.
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}