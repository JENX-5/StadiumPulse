"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, BarChart3, Bot, ChevronLeft, ChevronRight, History, Map, Settings, FileText, Users } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { DashboardView, useAppStore } from "@/store/useAppStore";
import { incidentsApi, resourcesApi } from "@/services/api";
import { Badge } from "@/components/ui/badge";

const navItems: { icon: typeof Map; label: string; view: DashboardView }[] = [
  { icon: Map, label: "Live Map", view: "map" },
  { icon: AlertTriangle, label: "Incidents", view: "incidents" },
  { icon: Users, label: "Resources", view: "resources" },
  { icon: Bot, label: "AI Agents", view: "agents" },
  { icon: History, label: "Timeline", view: "timeline" },
];

const secondaryItems = [
  { icon: BarChart3, label: "Analytics" },
  { icon: FileText, label: "Reports" },
  { icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const { activeView, setActiveView, venueId, timelineEvents } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);

  const { data: incidents = [] } = useQuery({
    queryKey: ["sidebar-incidents", venueId],
    queryFn: () => incidentsApi.listByVenue(venueId),
    enabled: !!venueId,
  });

  const { data: resources = [] } = useQuery({
    queryKey: ["sidebar-resources", venueId],
    queryFn: () => resourcesApi.list(venueId),
    enabled: !!venueId,
  });

  const activeIncidents = incidents.filter((incident) => incident.status.toLowerCase() === "open" || incident.status.toLowerCase() === "in_progress").length;
  const alerts = timelineEvents.filter((event) => (event.type || "").toLowerCase().includes("incident") || (event.type || "").toLowerCase().includes("alert")).length;
  const availableResources = resources.filter((resource) => resource.status.toLowerCase() === "available").length;

  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-border/60 bg-white/75 py-3 backdrop-blur-xl transition-[width] duration-300 dark:bg-slate-950/60",
        collapsed ? "w-16 lg:w-16" : "w-16 lg:w-[18rem]"
      )}
    >
      <div className="flex items-center justify-between px-2 pb-3 lg:px-3">
        <div className={cn("hidden lg:block", collapsed && "lg:hidden")}>
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Operations</div>
          <div className="text-sm font-semibold text-foreground">Control Rail</div>
        </div>
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="flex h-8 w-8 items-center justify-center rounded-xl border border-border/60 bg-background/70 text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex w-full flex-1 flex-col gap-1.5 px-2 lg:px-3">
        {navItems.map((item) => {
          const isActive = activeView === item.view;
          return (
            <motion.button
              key={item.label}
              onClick={() => setActiveView(item.view)}
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "group relative flex w-full items-center justify-center gap-3 rounded-xl p-2.5 text-left transition-all duration-200 lg:justify-start",
                isActive
                  ? "bg-foreground/10 text-foreground shadow-sm ring-1 ring-inset ring-border"
                  : "text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
              )}
            >
              <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors", isActive ? "bg-foreground/10" : "bg-muted/40 group-hover:bg-muted") }>
                <item.icon className={cn("h-4 w-4 shrink-0", isActive && "text-foreground")} />
              </span>
              <span className={cn("hidden flex-1 items-center justify-between gap-2 lg:flex", collapsed && "lg:hidden")}>
                <span className="text-sm font-medium">{item.label}</span>
                {item.view === "incidents" && activeIncidents > 0 && (
                  <Badge variant="secondary" className="rounded-full border-border/60 px-2 py-0 text-[10px] font-semibold">
                    {activeIncidents}
                  </Badge>
                )}
                {item.view === "timeline" && alerts > 0 && (
                  <Badge variant="secondary" className="rounded-full border-border/60 px-2 py-0 text-[10px] font-semibold">
                    {alerts}
                  </Badge>
                )}
              </span>
              {isActive && (
                <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-primary" />
              )}
            </motion.button>
          );
        })}

        <div className={cn("mt-3 hidden px-1 lg:block", collapsed && "lg:hidden")}>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Insights</div>
          <div className="space-y-1.5">
            {secondaryItems.map((item) => (
              <button
                key={item.label}
                type="button"
                disabled
                title="Coming soon"
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-muted-foreground opacity-60 transition-colors hover:bg-secondary/50"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/40">
                  <item.icon className="h-4 w-4" />
                </span>
                <span className="flex-1 text-sm font-medium">{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      <div className={cn("px-2 pt-3 lg:px-3", collapsed && "lg:hidden")}>
          <div className="rounded-2xl border border-border/60 bg-background/70 p-3 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Snapshot</div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div>
              <div className="text-muted-foreground">Incidents</div>
              <div className="font-semibold text-foreground">{activeIncidents}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Available</div>
              <div className="font-semibold text-foreground">{availableResources}</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
