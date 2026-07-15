"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, AlertCircle, Bot, Filter, Terminal } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TimelineEvent, useAppStore } from "@/store/useAppStore";

export function TimelineView() {
  const { timelineEvents } = useAppStore();
  const [filter, setFilter] = useState<"all" | "incident" | "agent" | "simulation">("all");

  const filtered = timelineEvents.filter((e) => {
    if (filter === "all") return true;
    return (e.type || "").toLowerCase().includes(filter);
  });

  const getEventIcon = (type: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("incident")) return <AlertCircle className="h-4 w-4 text-destructive" />;
    if (t.includes("agent") || t.includes("simulation")) return <Bot className="h-4 w-4 text-primary" />;
    return <Activity className="h-4 w-4 text-muted-foreground" />;
  };

  const getEventColor = (type: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("incident")) return "border-l-destructive";
    if (t.includes("agent")) return "border-l-primary";
    if (t.includes("simulation")) return "border-l-amber-500";
    return "border-l-muted-foreground";
  };

  const formatPayload = (payload: any) => {
    if (!payload) return "";
    try {
      return JSON.stringify(payload, null, 2);
    } catch {
      return String(payload);
    }
  };

  return (
    <div className="flex flex-col h-full p-4 lg:p-6 gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Event Timeline</h1>
        <Badge variant="secondary" className="text-xs font-mono">
          {timelineEvents.length} events
        </Badge>
      </div>

      {/* Filters */}
      <div className="flex rounded-lg border border-border overflow-hidden w-fit" role="group" aria-label="Filter timeline events">
        {(["all", "incident", "agent", "simulation"] as const).map((f) => (
          <button
            key={f}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              filter === f
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:bg-muted"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <ScrollArea className="flex-1 -mx-1" aria-live="polite" aria-atomic="false">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Terminal className="h-8 w-8 mb-3 opacity-40" />
            <p className="text-sm">No events recorded yet. Start a simulation to generate telemetry.</p>
          </div>
        ) : (
          <div className="space-y-1 px-1">
            <AnimatePresence initial={false}>
              {filtered.map((event: TimelineEvent) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`rounded-lg border border-border/40 bg-card/30 hover:bg-card/60 transition-colors p-3 border-l-2 ${getEventColor(event.type)}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 shrink-0">{getEventIcon(event.type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <Badge variant="outline" className="text-[9px] uppercase font-bold tracking-wider rounded-sm px-1.5">
                          {event.type}
                        </Badge>
                        <span className="text-[11px] text-muted-foreground font-mono">
                          {new Date(event.timestamp).toLocaleTimeString([], {
                            hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
                          })}
                        </span>
                      </div>
                      {event.payload && (
                        <pre className="text-[11px] text-muted-foreground font-mono whitespace-pre-wrap break-all mt-1 max-h-24 overflow-hidden">
                          {formatPayload(event.payload).substring(0, 200)}
                          {formatPayload(event.payload).length > 200 ? "…" : ""}
                        </pre>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
