"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Wifi,
  Sparkles,
  ShieldCheck,
  Radio,
  Clock3,
  Cpu,
  AlertTriangle,
  Waves,
} from "lucide-react";
import { motion } from "framer-motion";

import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { IncidentPanel } from "@/components/dashboard/IncidentPanel";
import { KPICards } from "@/components/metrics/KPICards";
import { MissionTimeline } from "@/components/timeline/MissionTimeline";
import { StadiumMap } from "@/components/map/StadiumMap";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { simulationApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";
import { SimulationControlPanel } from "@/components/simulation/SimulationControlPanel";

function useLiveClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return now;
}

function StatPill({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  tone?: "neutral" | "blue" | "green" | "amber" | "red";
}) {
  const toneClasses = {
    neutral: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700",
    blue: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700",
    green: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700",
    amber: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700",
    red: "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-700",
  }[tone];

  return (
    <div className={`flex items-center gap-3 rounded-xl px-3 py-2 ring-1 ${toneClasses}`}>
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/70 dark:bg-white/10">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] opacity-70">{label}</div>
        <div className="truncate text-sm font-semibold leading-tight">{value}</div>
      </div>
    </div>
  );
}

function OperationalHealthCard() {
  const { liveState, timelineEvents } = useAppStore();
  const { data: simulationStatus } = useQuery({
    queryKey: ["simulation-status"],
    queryFn: () => simulationApi.getStatus(),
    refetchInterval: 4000,
  });

  const activeIncidents = liveState?.active_incidents ?? 0;
  const crowdDensity = liveState?.global_crowd_density ?? 0.15;
  const availableResources = liveState?.available_resources ?? 0;
  const aiActive = timelineEvents.some((event) => event.type.includes("agent"));

  const health = useMemo(() => {
    if (activeIncidents >= 8 || crowdDensity >= 0.78) return { label: "Critical", tone: "red" as const };
    if (activeIncidents >= 4 || crowdDensity >= 0.55) return { label: "Attention", tone: "amber" as const };
    return { label: "Nominal", tone: "green" as const };
  }, [activeIncidents, crowdDensity]);

  return (
    <Card className="overflow-hidden border-border/60 bg-white/90 shadow-sm backdrop-blur dark:bg-card/90">
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm font-semibold tracking-tight text-foreground">Operational Health</CardTitle>
          <Badge
            variant="outline"
            className={`rounded-full px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em] ${
              health.tone === "green"
                ? "border-border/70 bg-background text-foreground"
                : health.tone === "amber"
                  ? "border-border/70 bg-muted/70 text-muted-foreground"
                  : "border-border/70 bg-muted text-foreground"
            }`}
          >
            {health.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 px-4 py-4">
        <StatPill icon={ShieldCheck} label="Connection" value={liveState ? "WebSocket synced" : "Awaiting sync"} tone={liveState ? "green" : "amber"} />
        <StatPill icon={Sparkles} label="AI status" value={aiActive ? "Agents active" : "Monitoring"} tone={aiActive ? "blue" : "neutral"} />
        <StatPill
          icon={Radio}
          label="Simulation"
          value={simulationStatus ? (simulationStatus.is_running ? (simulationStatus.is_paused ? "Paused" : "Running") : "Stopped") : "Loading..."}
          tone={simulationStatus?.is_running ? (simulationStatus.is_paused ? "amber" : "green") : "neutral"}
        />
        <StatPill icon={Waves} label="Crowd pressure" value={`${Math.round(crowdDensity * 100)}% density`} tone={crowdDensity >= 0.55 ? "amber" : "blue"} />
        <StatPill icon={Cpu} label="Available units" value={`${availableResources} deployed-ready`} tone="neutral" />
      </CardContent>
    </Card>
  );
}

export function CommandCenterDashboard() {
  const clock = useLiveClock();
  const { liveState, timelineEvents } = useAppStore();
  const recentAlerts = timelineEvents.filter((event) => event.type.includes("incident") || event.type.includes("alert")).slice(0, 3);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 px-3 py-3 lg:px-4 lg:py-4 2xl:px-5 2xl:py-5">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-2 xl:grid-cols-6"
      >
        <StatPill icon={Activity} label="Venue" value="Demo Stadium" tone="blue" />
        <StatPill icon={Clock3} label="Live clock" value={clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })} tone="neutral" />
        <StatPill icon={Wifi} label="Telemetry" value={liveState ? "Connected" : "Syncing"} tone={liveState ? "green" : "amber"} />
        <StatPill icon={Sparkles} label="AI engine" value={timelineEvents.some((event) => event.type.includes("agent")) ? "Predictive active" : "Standing by"} tone="blue" />
        <StatPill icon={Radio} label="System load" value={liveState ? `${Math.round((liveState.global_crowd_density ?? 0.15) * 100)}% crowd pressure` : "Awaiting data"} tone="amber" />
        <StatPill icon={AlertTriangle} label="Alert buffer" value={`${recentAlerts.length} recent`} tone={recentAlerts.length > 0 ? "red" : "green"} />
      </motion.div>

      <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(320px,360px)_minmax(0,1fr)_minmax(320px,380px)]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
          className="flex min-h-0 flex-col gap-3"
        >
          <KPICards />
          <SimulationControlPanel />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1 }}
          className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border/60 bg-white/90 shadow-sm backdrop-blur dark:bg-card/90"
        >
          <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Primary operations view</div>
              <div className="text-sm font-medium text-foreground">Stadium crowd control, incident response, and resource dispatch</div>
            </div>
            <Badge variant="outline" className="rounded-full border-border/60 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.18em]">
              Live command center
            </Badge>
          </div>
          <div className="min-h-0 flex-1 p-3 lg:p-4">
            <StadiumMap />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.15 }}
          className="flex min-h-0 flex-col gap-3"
        >
          <AIInsightsPanel />
          <OperationalHealthCard />
          <IncidentPanel />
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.2 }}
        className="min-h-[280px] overflow-hidden rounded-2xl border border-border/60 bg-white/90 shadow-sm backdrop-blur dark:bg-card/90"
      >
        <MissionTimeline />
      </motion.div>
    </div>
  );
}