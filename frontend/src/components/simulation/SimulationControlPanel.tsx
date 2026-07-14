"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertOctagon, Gauge, Pause, Play, Radio, Square } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api-client";
import { incidentsApi, simulationApi, zonesApi } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";
import { IncidentCreate } from "@/types/api";

const SEVERITY_OPTIONS: { value: IncidentCreate["severity"]; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

export function SimulationControlPanel() {
  const { venueId, timelineEvents } = useAppStore();
  const queryClient = useQueryClient();

  const [speed, setSpeed] = useState(1);
  const [deterministic, setDeterministic] = useState(false);

  const [zoneId, setZoneId] = useState<string>("");
  const [severity, setSeverity] = useState<IncidentCreate["severity"]>("medium");
  const [description, setDescription] = useState("");
  const [injectMessage, setInjectMessage] = useState<string | null>(null);

  const { data: status } = useQuery({
    queryKey: ["simulation-status"],
    queryFn: () => simulationApi.getStatus(),
    // Playback state can change from outside this panel (another tab, a
    // teammate, a restart) — light polling keeps the badge/buttons honest
    // without needing a dedicated WS message for engine state itself.
  });

  const { data: zones = [] } = useQuery({
    queryKey: ["zones", venueId],
    queryFn: () => zonesApi.list(venueId),
  });

  const [controlError, setControlError] = useState<string | null>(null);

  const controlMutation = useMutation({
    mutationFn: simulationApi.control,
    onSuccess: (data) => {
      setControlError(null);
      queryClient.setQueryData(["simulation-status"], data);
    },
    onError: (err) => {
      setControlError(err instanceof ApiError ? err.message : "Simulation control failed.");
    },
  });

  const injectMutation = useMutation({
    mutationFn: incidentsApi.create,
    onSuccess: () => {
      setInjectMessage("Incident injected — check the Active Incidents panel.");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["incidents", venueId] });
    },
    onError: (err) => {
      setInjectMessage(err instanceof ApiError ? err.message : "Failed to inject incident.");
    },
  });

  const lastTick = useMemo(
    () => timelineEvents.find((event) => event.type === "simulation.tick"),
    [timelineEvents]
  );

  const isRunning = status?.is_running ?? false;
  const isPaused = status?.is_paused ?? false;

  function handleStart() {
    controlMutation.mutate({
      command: "start",
      venue_id: venueId,
      speed_multiplier: speed,
      deterministic,
    });
  }

  function handlePauseResume() {
    controlMutation.mutate({
      command: isPaused ? "resume" : "pause",
      venue_id: venueId,
      speed_multiplier: speed,
    });
  }

  function handleStop() {
    controlMutation.mutate({ command: "stop", venue_id: venueId });
  }

  function handleSpeedChange(value: number) {
    setSpeed(value);
    // Live-adjust speed while running, rather than only applying it on the next start.
    if (isRunning) {
      controlMutation.mutate({
        command: isPaused ? "pause" : "resume",
        venue_id: venueId,
        speed_multiplier: value,
      });
    }
  }

  function handleInjectIncident() {
    if (!description.trim()) {
      setInjectMessage("Add a short description before injecting the incident.");
      return;
    }
    setInjectMessage(null);
    injectMutation.mutate({
      venue_id: venueId,
      zone_id: zoneId || null,
      raw_text: description.trim(),
      severity,
      source: "simulation",
    });
  }

  return (
    <Card className="overflow-hidden border-border/60 bg-white/90 shadow-sm backdrop-blur dark:bg-card/90">
      <CardHeader className="border-b border-border/50 bg-muted/20 px-4 py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground">
            <Radio className="h-4 w-4" />
            Simulation
          </CardTitle>
          <Badge variant={isRunning && !isPaused ? "default" : "secondary"} className="rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em]">
            {isRunning ? (isPaused ? "Paused" : "Running") : "Stopped"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-3">
        <Tabs defaultValue="playback">
          <TabsList className="w-full bg-muted/40">
            <TabsTrigger value="playback" className="flex-1">
              Playback
            </TabsTrigger>
            <TabsTrigger value="inject" className="flex-1">
              Inject Incident
            </TabsTrigger>
          </TabsList>

          <TabsContent value="playback" className="pt-3 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={isRunning ? "outline" : "default"}
                className="flex-1 rounded-xl"
                disabled={isRunning || controlMutation.isPending}
                onClick={handleStart}
              >
                <Play className="h-3.5 w-3.5" />
                Start
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 rounded-xl"
                disabled={!isRunning || controlMutation.isPending}
                onClick={handlePauseResume}
              >
                <Pause className="h-3.5 w-3.5" />
                {isPaused ? "Resume" : "Pause"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 rounded-xl text-destructive hover:text-destructive"
                disabled={!isRunning || controlMutation.isPending}
                onClick={handleStop}
              >
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1.5 font-medium uppercase tracking-wider">
                  <Gauge className="h-3.5 w-3.5" />
                  Speed
                </span>
                <span className="font-mono text-foreground">{speed.toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min={0.5}
                max={10}
                step={0.5}
                value={speed}
                onChange={(event) => handleSpeedChange(Number(event.target.value))}
                className="w-full accent-primary"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={deterministic}
                onChange={(event) => setDeterministic(event.target.checked)}
                className="accent-primary"
              />
              Deterministic mode (fixed seed, reproducible run)
            </label>

            <div className="text-[11px] text-muted-foreground border-t border-border/40 pt-2">
              {lastTick
                ? `Last tick: ${new Date(lastTick.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}`
                : "No ticks received yet."}
            </div>

            {controlError && (
              <p className="text-[11px] text-destructive font-medium mt-1">{controlError}</p>
            )}
          </TabsContent>

          <TabsContent value="inject" className="pt-3 flex flex-col gap-2.5">
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Zone
              </label>
              <select
                value={zoneId}
                onChange={(event) => setZoneId(event.target.value)}
                className="h-9 rounded-xl border border-border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="">Unassigned / venue-wide</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Severity
              </label>
              <div className="flex gap-1.5">
                {SEVERITY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSeverity(option.value)}
                    className={`flex-1 rounded-xl border px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                      severity === option.value
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Description
              </label>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={3}
                placeholder="e.g. Reported medical emergency near Section 114 concourse"
                className="resize-none rounded-xl border border-border bg-background px-3 py-2.5 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              />
            </div>

            <Button
              size="sm"
              onClick={handleInjectIncident}
              disabled={injectMutation.isPending}
              className="w-full rounded-xl"
            >
              <AlertOctagon className="h-3.5 w-3.5" />
              Inject Incident
            </Button>

            {injectMessage && (
              <p className="text-[11px] text-muted-foreground">{injectMessage}</p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
