"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Clock3, ShieldCheck, Users } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import { motion } from "framer-motion";

import { Card, CardContent } from "@/components/ui/card";
import { incidentsApi, resourcesApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/lib/utils";

type MetricTone = "blue" | "green" | "amber" | "red" | "slate";

function buildSeries(values: number[], fallback: number, points = 8) {
  const source = values.length > 0 ? values.slice(-points) : Array.from({ length: points }, () => fallback);
  const padded = source.length < points ? [...Array.from({ length: points - source.length }, () => source[0] ?? fallback), ...source] : source;
  return padded.map((value, index) => ({ index, value }));
}

function TrendSparkline({ data, tone }: { data: { index: number; value: number }[]; tone: MetricTone }) {
  const stroke = tone === "red" ? "#111111" : tone === "amber" ? "#374151" : tone === "green" ? "#111111" : "#6b7280";

  return (
    <div className="h-14 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Tooltip cursor={false} content={() => null} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={stroke}
            strokeWidth={2}
            dot={false}
            activeDot={false}
            strokeLinecap="round"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  tone,
  trend,
  sparkline,
}: {
  label: string;
  value: string;
  description: string;
  icon: typeof AlertTriangle;
  tone: MetricTone;
  trend: string;
  sparkline: { index: number; value: number }[];
}) {
  const toneClasses = {
    blue: "from-slate-500/10 to-slate-500/5 text-slate-700 ring-slate-200 dark:from-slate-500/20 dark:to-slate-500/10 dark:text-slate-200 dark:ring-slate-500/20",
    green: "from-slate-500/10 to-slate-500/5 text-slate-700 ring-slate-200 dark:from-slate-500/20 dark:to-slate-500/10 dark:text-slate-200 dark:ring-slate-500/20",
    amber: "from-slate-500/10 to-slate-500/5 text-slate-700 ring-slate-200 dark:from-slate-500/20 dark:to-slate-500/10 dark:text-slate-200 dark:ring-slate-500/20",
    red: "from-slate-500/10 to-slate-500/5 text-slate-700 ring-slate-200 dark:from-slate-500/20 dark:to-slate-500/10 dark:text-slate-200 dark:ring-slate-500/20",
    slate: "from-slate-500/10 to-slate-500/5 text-slate-600 ring-slate-100 dark:from-slate-500/20 dark:to-slate-500/10 dark:text-slate-200 dark:ring-slate-500/20",
  }[tone];

  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.2 }}>
      <Card className="overflow-hidden border-border/60 bg-white/90 shadow-sm backdrop-blur transition-shadow hover:shadow-lg dark:bg-card/90">
        <CardContent className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className={cn("flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ring-1", toneClasses)}>
              <Icon className="h-5 w-5" />
            </div>
            <div className={cn("rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ring-1", toneClasses)}>
              {trend}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">{label}</div>
            <div className="mt-1 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
            <div className="mt-1 text-sm leading-snug text-muted-foreground">{description}</div>
          </div>

          <TrendSparkline data={sparkline} tone={tone} />
        </CardContent>
      </Card>
    </motion.div>
  );
}

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
  const activeIncidents = incidents.filter((incident) => String(incident.status).toLowerCase() === "open" || String(incident.status).toLowerCase() === "in_progress").length;
  const availableResources = resources.filter((resource) => String(resource.status).toLowerCase() === "available").length;
  const totalResources = resources.length;

  const avgResponseMs =
    activeIncidents > 0
      ? incidents
          .filter((incident) => String(incident.status).toLowerCase() === "open" || String(incident.status).toLowerCase() === "in_progress")
          .reduce((sum, incident) => sum + (Date.now() - new Date(incident.created_at).getTime()), 0) / activeIncidents
      : 0;

  const avgMinutes = Math.floor(avgResponseMs / 60000);
  const avgSeconds = Math.floor((avgResponseMs % 60000) / 1000);

  const incidentSpark = useMemo(() => {
    const now = Date.now();
    const bucketSize = 5 * 60 * 1000;
    const buckets = Array.from({ length: 8 }, (_, index) => {
      const start = now - bucketSize * (8 - index);
      const end = start + bucketSize;
      return incidents.filter((incident) => {
        const createdAt = new Date(incident.created_at).getTime();
        return createdAt >= start && createdAt < end;
      }).length;
    });
    return buildSeries(buckets, activeIncidents, 8);
  }, [activeIncidents, incidents]);

  const densitySpark = useMemo(() => buildSeries(liveState?.risk_history ?? [], density * 100, 8), [density, liveState?.risk_history]);

  const resourcesSpark = useMemo(() => {
    const values = [availableResources, totalResources - availableResources, Math.max(totalResources - availableResources - 1, 0), availableResources];
    return buildSeries(values, availableResources, 8);
  }, [availableResources, totalResources]);

  const responseSpark = useMemo(() => {
    const responseValues = incidents
      .filter((incident) => String(incident.status).toLowerCase() === "open" || String(incident.status).toLowerCase() === "in_progress")
      .map((incident) => Math.max((Date.now() - new Date(incident.created_at).getTime()) / 60000, 0));
    return buildSeries(responseValues, avgMinutes || 1, 8);
  }, [avgMinutes, incidents]);

  const incidentTrend = activeIncidents > 0 ? `+${Math.max(activeIncidents - (incidentSpark[0]?.value ?? activeIncidents), 0)} in last 40m` : "Stable";
  const densityTrend = density >= 0.55 ? "Elevated pressure" : density >= 0.35 ? "Watch trend" : "Within band";
  const resourceTrend = availableResources < totalResources * 0.7 ? "Deployments in use" : "Capacity healthy";
  const responseTrend = activeIncidents > 0 ? `+${avgMinutes}m ${avgSeconds}s avg` : "No open incidents";

  return (
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 xl:grid-cols-1">
      <MetricCard
        label="Active Incidents"
        value={String(activeIncidents)}
        description="Open or in-progress incidents currently being monitored."
        icon={AlertTriangle}
        tone={activeIncidents > 0 ? "red" : "green"}
        trend={incidentTrend}
        sparkline={incidentSpark}
      />
      <MetricCard
        label="Crowd Density"
        value={`${(density * 100).toFixed(1)}%`}
        description="Global crowd pressure derived from the live telemetry stream."
        icon={Users}
        tone={density >= 0.55 ? "amber" : "blue"}
        trend={densityTrend}
        sparkline={densitySpark}
      />
      <MetricCard
        label="Resource Readiness"
        value={`${availableResources}/${totalResources}`}
        description="Available response units ready for dispatch across the venue."
        icon={ShieldCheck}
        tone={availableResources < totalResources * 0.7 ? "amber" : "green"}
        trend={resourceTrend}
        sparkline={resourcesSpark}
      />
      <MetricCard
        label="Avg Response"
        value={activeIncidents > 0 ? `${avgMinutes}m ${avgSeconds}s` : "—"}
        description="Average elapsed time for currently active incident handling."
        icon={Clock3}
        tone={activeIncidents > 0 ? "blue" : "slate"}
        trend={responseTrend}
        sparkline={responseSpark}
      />
    </div>
  );
}