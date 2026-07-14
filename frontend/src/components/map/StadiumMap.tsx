"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  Ambulance,
  Camera,
  ChevronDown,
  ChevronUp,
  CircleDashed,
  Eye,
  Flag,
  Layers3,
  MapPinned,
  Minus,
  Plus,
  Route,
  ShieldAlert,
  ShieldCheck,
  HeartPulse,
  HardHat,
  UserSquare2,
  RotateCcw,
} from "lucide-react";
import { motion } from "framer-motion";

import { useAppStore } from "@/store/useAppStore";
import { incidentsApi, resourcesApi, zonesApi } from "@/services/api";
import { RiskHeatmap, ZONE_CENTERS } from "../heatmap/RiskHeatmap";
import { Badge } from "@/components/ui/badge";

const infrastructureMarkers = [
  { id: "gate-a", label: "Gate A", icon: Flag, x: 118, y: 292, tone: "blue" },
  { id: "gate-b", label: "Gate B", icon: Flag, x: 684, y: 302, tone: "amber" },
  { id: "med-east", label: "Medical", icon: HeartPulse, x: 570, y: 420, tone: "green" },
  { id: "camera-ring", label: "Camera", icon: Camera, x: 400, y: 120, tone: "blue" },
  { id: "security-core", label: "Security", icon: ShieldCheck, x: 400, y: 482, tone: "blue" },
  { id: "ambulance-bay", label: "Ambulance", icon: Ambulance, x: 92, y: 520, tone: "red" },
  { id: "routing", label: "Evac Route", icon: Route, x: 400, y: 250, tone: "amber" },
];

const layerLabels = [
  { key: "heatmap", label: "Heatmap" },
  { key: "incidents", label: "Incidents" },
  { key: "resources", label: "Resources" },
  { key: "infrastructure", label: "Infrastructure" },
  { key: "routes", label: "Routes" },
] as const;

function toneClasses(tone: string) {
  switch (tone) {
    case "green":
      return "bg-slate-900 text-white border-slate-300";
    case "amber":
      return "bg-slate-700 text-white border-slate-300";
    case "red":
      return "bg-slate-950 text-white border-slate-300";
    default:
      return "bg-slate-800 text-white border-slate-300";
  }
}

export function StadiumMap() {
  const { liveState, venueId } = useAppStore();
  const [zoom, setZoom] = useState(1);
  const [layers, setLayers] = useState({
    heatmap: true,
    incidents: true,
    resources: true,
    infrastructure: true,
    routes: true,
  });

  const { data: zones = [], isLoading: zonesLoading, isError: zonesError } = useQuery({
    queryKey: ["zones", venueId],
    queryFn: () => (venueId ? zonesApi.list(venueId) : Promise.resolve([])),
    enabled: !!venueId,
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ["incidents", venueId],
    queryFn: () => (venueId ? incidentsApi.listByVenue(venueId) : Promise.resolve([])),
    enabled: !!venueId,
  });

  const { data: resources = [] } = useQuery({
    queryKey: ["resources", venueId],
    queryFn: () => (venueId ? resourcesApi.list(venueId) : Promise.resolve([])),
    enabled: !!venueId,
  });

  const zoneIdToCenter = useMemo(() => {
    const map = new Map<string, { cx: number; cy: number; r: number }>();
    zones.forEach((zone) => {
      const center = ZONE_CENTERS[zone.name];
      if (center) map.set(zone.id, center);
    });
    return map;
  }, [zones]);

  const activeIncidents = incidents.filter((incident) => incident.status !== "resolved" && incident.status !== "closed");

  const highestPressureZone = useMemo(() => {
    const riskByZone = new Map<string, number>();
    activeIncidents.forEach((incident) => {
      if (!incident.zone_id) return;
      riskByZone.set(incident.zone_id, (riskByZone.get(incident.zone_id) ?? 0) + 1);
    });

    const candidates = zones
      .map((zone) => ({ zone, risk: riskByZone.get(zone.id) ?? 0 }))
      .sort((a, b) => b.risk - a.risk);

    return candidates[0] ?? null;
  }, [activeIncidents, zones]);

  const crowdDensity = liveState?.global_crowd_density ?? 0.15;
  const predictedMinutes = Math.max(4, Math.round(18 - crowdDensity * 12));

  const getJitter = (id: string, index: number, radiusBase: number = 30) => {
    const hash = id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const angle = (hash + index * 45) * (Math.PI / 180);
    const radius = radiusBase + (hash % 24);
    return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  };

  return (
    <div className="relative h-full min-h-[520px] w-full overflow-hidden rounded-2xl border border-border/60 bg-slate-950/5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)] dark:bg-slate-900/20">
      <div className="pointer-events-none absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "radial-gradient(circle at 2px 2px, currentColor 1px, transparent 0)", backgroundSize: "32px 32px" }} />

      <div className="absolute left-4 top-4 z-40 flex items-center gap-2">
        <Badge className="rounded-full border-border/60 bg-background/85 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground shadow-sm backdrop-blur">
          <span className="relative mr-2 flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-slate-900 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-slate-900" />
          </span>
          {liveState ? "Live telemetry synced" : "Awaiting telemetry"}
        </Badge>
        {crowdDensity > 0.35 && (
          <Badge className="rounded-full border-border/70 bg-background px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-foreground">
            Predicted surge in {predictedMinutes}m
          </Badge>
        )}
      </div>

      <div className="absolute right-4 top-4 z-40 flex flex-col items-end gap-2">
        <div className="flex items-center gap-1 rounded-2xl border border-border/60 bg-background/85 p-1 shadow-sm backdrop-blur">
          <button
            type="button"
            onClick={() => setZoom((value) => Math.max(0.85, Number((value - 0.1).toFixed(2))))}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Zoom out"
          >
            <Minus className="h-4 w-4" />
          </button>
          <div className="min-w-10 px-2 text-center text-[11px] font-semibold text-foreground">{Math.round(zoom * 100)}%</div>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Reset zoom"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoom((value) => Math.min(1.2, Number((value + 0.1).toFixed(2))))}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="Zoom in"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-wrap justify-end gap-1.5 rounded-2xl border border-border/60 bg-background/85 p-2 shadow-sm backdrop-blur">
          {layerLabels.map((layer) => (
            <button
              key={layer.key}
              type="button"
              onClick={() => setLayers((current) => ({ ...current, [layer.key]: !current[layer.key] }))}
              className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] transition-colors ${
                layers[layer.key]
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/70 text-muted-foreground hover:bg-muted"
              }`}
            >
              {layer.label}
            </button>
          ))}
        </div>
      </div>

      <div className="absolute bottom-4 left-4 z-40 flex flex-wrap gap-2 rounded-2xl border border-border/60 bg-background/85 p-2 shadow-sm backdrop-blur">
        {[
          { label: "Crowd surge", tone: "red" },
          { label: "Security", tone: "blue" },
          { label: "Medical", tone: "green" },
          { label: "Evacuation", tone: "amber" },
        ].map((entry) => (
          <div key={entry.label} className="flex items-center gap-2 rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            <span className={`h-2.5 w-2.5 rounded-full ${entry.tone === "red" ? "bg-red-500" : entry.tone === "green" ? "bg-emerald-500" : entry.tone === "amber" ? "bg-amber-500" : "bg-blue-500"}`} />
            <span className={`h-2.5 w-2.5 rounded-full ${entry.tone === "red" ? "bg-slate-950" : entry.tone === "green" ? "bg-slate-800" : entry.tone === "amber" ? "bg-slate-600" : "bg-slate-400"}`} />
            {entry.label}
          </div>
        ))}
      </div>

      {zonesLoading ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-border/60 bg-background/85 px-6 py-5 shadow-lg backdrop-blur">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Loading map data…</span>
          </div>
        </div>
      ) : zonesError ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-border/60 bg-background/85 px-6 py-5 text-center shadow-lg backdrop-blur">
            <span className="text-sm font-medium text-foreground">Failed to load map data.</span>
            <span className="text-xs text-muted-foreground">Check that the backend is running.</span>
          </div>
        </div>
      ) : (
        <motion.div
          className="absolute inset-0 flex items-center justify-center p-6 pt-16 pb-16 lg:pr-12"
          animate={{ scale: zoom }}
          transition={{ type: "spring", stiffness: 220, damping: 24 }}
          style={{ transformOrigin: "center center" }}
        >
          <div className="relative h-full w-full">
            {layers.heatmap && <RiskHeatmap />}

            {layers.routes && (
              <svg viewBox="0 0 800 600" className="absolute inset-0 z-15 h-full w-full pointer-events-none text-primary/35" fill="none" stroke="currentColor">
                <path d="M120 292 C 210 250, 270 210, 330 205" strokeWidth="2" strokeDasharray="8 8" />
                <path d="M684 302 C 620 260, 560 230, 510 210" strokeWidth="2" strokeDasharray="8 8" />
                <path d="M92 520 C 170 470, 240 420, 310 360" strokeWidth="1.5" strokeDasharray="6 8" />
                <path d="M570 420 C 520 390, 475 360, 430 330" strokeWidth="1.5" strokeDasharray="6 8" />
              </svg>
            )}

            <svg viewBox="0 0 800 600" className="absolute inset-0 z-20 h-full w-full text-primary" stroke="currentColor" fill="none">
              <rect x="50" y="50" width="700" height="500" rx="200" strokeWidth="1.5" className="opacity-40" />
              <rect x="100" y="100" width="600" height="400" rx="150" strokeWidth="1" strokeDasharray="4 6" className="opacity-40" />
              <rect x="150" y="150" width="500" height="300" rx="100" strokeWidth="0.5" className="opacity-40" />

              <rect x="250" y="200" width="300" height="200" rx="10" strokeWidth="2" fill="currentColor" fillOpacity="0.04" className="opacity-40" />
              <circle cx="400" cy="300" r="40" strokeWidth="1" className="opacity-40" />
              <line x1="400" y1="200" x2="400" y2="400" strokeWidth="1" className="opacity-40" />

              <line x1="50" y1="300" x2="150" y2="300" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
              <line x1="650" y1="300" x2="750" y2="300" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
              <line x1="400" y1="50" x2="400" y2="150" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
              <line x1="400" y1="450" x2="400" y2="550" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />

              {activeIncidents
                .filter((incident) => incident.zone_id)
                .map((incident, index) => {
                  if (!incident.zone_id) return null;
                  const center = zoneIdToCenter.get(incident.zone_id);
                  if (!center || !layers.incidents) return null;
                  const jitter = getJitter(incident.id, index, 40);
                  const x = center.cx + jitter.x;
                  const y = center.cy + jitter.y;

                  return (
                    <g key={incident.id} transform={`translate(${x - 16}, ${y - 16})`}>
                      <foreignObject width="150" height="150" className="overflow-visible pointer-events-auto">
                        <div className="relative group h-8 w-8 cursor-pointer">
                          <div className="absolute -inset-1 rounded-full bg-red-500/25 animate-ping" />
                          <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-red-300 bg-red-500 text-white shadow-lg">
                            <AlertCircle className="h-4 w-4" />
                          </div>
                          <div className="absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-white/10 bg-slate-950 px-3 py-1.5 text-[11px] font-medium text-white opacity-0 shadow-xl transition-opacity group-hover:opacity-100 pointer-events-none z-50">
                            <span className="mr-1 font-bold text-red-400">[{incident.severity}]</span>
                            {incident.raw_text.substring(0, 40)}{incident.raw_text.length > 40 ? "..." : ""}
                          </div>
                        </div>
                      </foreignObject>
                    </g>
                  );
                })}

              {layers.resources &&
                resources.map((resource, index) => {
                  if (!resource.current_zone_id) return null;
                  const center = zoneIdToCenter.get(resource.current_zone_id);
                  if (!center) return null;
                  const jitter = getJitter(resource.id, index + 17, 22);
                  const x = center.cx + jitter.x;
                  const y = center.cy + jitter.y;

                  let Icon = ShieldAlert;
                  let tone = "blue";
                  if (resource.resource_type === "medical") {
                    Icon = HeartPulse;
                    tone = "green";
                  } else if (resource.resource_type === "maintenance" || resource.resource_type === "cleaning") {
                    Icon = HardHat;
                    tone = "amber";
                  } else if (resource.resource_type === "volunteer") {
                    Icon = UserSquare2;
                    tone = "purple";
                  }

                  return (
                    <g key={resource.id} transform={`translate(${x - 14}, ${y - 14})`}>
                      <foreignObject width="110" height="110" className="overflow-visible pointer-events-auto">
                        <div className="relative group h-7 w-7 cursor-pointer">
                          <div className={`relative flex h-7 w-7 items-center justify-center rounded-full border shadow-md ${tone === "green" ? "bg-emerald-500 border-emerald-300" : tone === "amber" ? "bg-amber-500 border-amber-300" : tone === "purple" ? "bg-violet-500 border-violet-300" : "bg-blue-500 border-blue-300"}`}>
                            <Icon className="h-3.5 w-3.5 text-white" />
                          </div>
                          <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border/40 bg-background px-2 py-1 text-[10px] text-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 pointer-events-none z-50">
                            {resource.label}
                          </div>
                        </div>
                      </foreignObject>
                    </g>
                  );
                })}

              {layers.infrastructure &&
                infrastructureMarkers.map((marker) => {
                  const Icon = marker.icon;
                  return (
                    <g key={marker.id} transform={`translate(${marker.x - 18}, ${marker.y - 18})`}>
                      <foreignObject width="140" height="100" className="overflow-visible pointer-events-auto">
                        <div className="relative group h-9 w-9 cursor-pointer">
                          <div className={`absolute -inset-1 rounded-full opacity-60 animate-pulse ${marker.tone === "red" ? "bg-red-500/20" : marker.tone === "amber" ? "bg-amber-500/20" : marker.tone === "green" ? "bg-emerald-500/20" : "bg-blue-500/20"}`} />
                          <div className={`relative flex h-9 w-9 items-center justify-center rounded-full border shadow-md ${toneClasses(marker.tone)}`}>
                            <Icon className="h-4 w-4" />
                          </div>
                          <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border/40 bg-background px-2 py-1 text-[10px] text-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 pointer-events-none z-50">
                            {marker.label}
                          </div>
                        </div>
                      </foreignObject>
                    </g>
                  );
                })}

              {layers.infrastructure && highestPressureZone && highestPressureZone.zone && zoneIdToCenter.has(highestPressureZone.zone.id) && highestPressureZone.risk > 0 && (
                <g transform={`translate(${zoneIdToCenter.get(highestPressureZone.zone.id)!.cx - 70}, ${zoneIdToCenter.get(highestPressureZone.zone.id)!.cy - 60})`}>
                  <foreignObject width="180" height="80" className="overflow-visible pointer-events-none">
                    <div className="rounded-2xl border border-amber-200 bg-background/90 px-3 py-2 shadow-lg backdrop-blur">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-600">AI forecast</div>
                      <div className="text-sm font-semibold text-foreground">{highestPressureZone.zone.name}</div>
                      <div className="text-[11px] text-muted-foreground">Incident pressure is rising in this sector.</div>
                    </div>
                  </foreignObject>
                </g>
              )}
            </svg>
          </div>
        </motion.div>
      )}
    </div>
  );
}