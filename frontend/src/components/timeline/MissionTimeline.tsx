import { AnimatePresence, motion } from "framer-motion";
import { Activity, AlertCircle, Bot, Terminal } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { TimelineEvent, useAppStore } from "@/store/useAppStore";

export function MissionTimeline() {
  const { timelineEvents } = useAppStore();

  const getEventIcon = (type: string) => {
    if (type.includes("incident")) return <AlertCircle className="h-3 w-3 text-destructive" />;
    if (type.includes("agent") || type.includes("simulation")) return <Bot className="h-3 w-3 text-primary" />;
    return <Activity className="h-3 w-3 text-muted-foreground" />;
  };

  const formatPayload = (payload: any) => {
    if (!payload) return "";
    try {
      return JSON.stringify(payload).substring(0, 100) + (JSON.stringify(payload).length > 100 ? "..." : "");
    } catch {
      return String(payload);
    }
  };

  return (
    <div className="h-48 w-full bg-[#0a0a0a] border-t border-border/40 flex flex-col relative overflow-hidden">
      {/* Console Header */}
      <div className="h-8 border-b border-border/20 bg-muted/10 flex items-center px-4 gap-2 shrink-0">
        <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          Live Operational Telemetry
        </span>
      </div>

      <ScrollArea className="flex-1 px-4 py-2">
        <div className="flex flex-col gap-1 justify-end min-h-full">
          <AnimatePresence initial={false}>
            {timelineEvents.map((event: TimelineEvent) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -20, height: 0 }}
                animate={{ opacity: 1, x: 0, height: "auto" }}
                exit={{ opacity: 0 }}
                className="font-mono text-[11px] py-1 border-b border-border/10 flex items-start gap-3"
              >
                <div className="shrink-0 mt-0.5">{getEventIcon(event.type)}</div>
                <div className="text-muted-foreground shrink-0 w-16">
                  {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
                <div className="text-primary/90 font-semibold shrink-0 w-40 truncate">
                  [{event.type.toUpperCase()}]
                </div>
                <div className="text-muted-foreground truncate">
                  {formatPayload(event.payload)}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {timelineEvents.length === 0 && (
            <div className="text-[11px] font-mono text-muted-foreground italic py-4">
              Awaiting incoming event streams...
            </div>
          )}
        </div>
      </ScrollArea>
      
      {/* Decorative gradient mask for smooth scrolling at top */}
      <div className="absolute top-8 left-0 right-0 h-8 bg-gradient-to-b from-[#0a0a0a] to-transparent pointer-events-none" />
    </div>
  );
}
