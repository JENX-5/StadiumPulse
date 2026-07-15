"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BrainCircuit, ChevronRight, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";
import { memoryApi } from "@/services/api";
import { TournamentMemory } from "@/types/api";
import { cn } from "@/lib/utils";

function ConfidenceRing({ confidence }: { confidence: number }) {
  const strokeDasharray = `${confidence * 2.35} 235`;

  return (
    <div className="relative flex h-16 w-16 items-center justify-center rounded-full border border-border/60 bg-white shadow-sm dark:bg-slate-950/40">
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full -rotate-90">
        <circle cx="50" cy="50" r="37" fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-200 dark:text-slate-700" />
        <circle
          cx="50"
          cy="50"
          r="37"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          className="text-slate-900 dark:text-slate-100"
        />
      </svg>
      <div className="relative text-center">
        <div className="text-xl font-bold text-foreground">{confidence}%</div>
      </div>
    </div>
  );
}

export function AIInsightsPanel() {
  const { liveState, venueId, riskHistory } = useAppStore();
  const [latestMemory, setLatestMemory] = useState<TournamentMemory | null>(null);

  useEffect(() => {
    if (!venueId) return;
    memoryApi
      .list(venueId)
      .then((memories) => {
        if (memories.length > 0) {
          setLatestMemory(memories[0] ?? null);
        }
      })
      .catch((err) => console.error("Failed to fetch memories", err));
  }, [venueId]);

  const density = liveState?.global_crowd_density ?? 0.15;
  const confidence = Math.min(99, Math.max(78, Math.round(82 + density * 20)));
  const predictedMinutes = Math.max(4, Math.round(16 - density * 14));
  const estimatedImpact = density > 0.6 ? "High" : density > 0.35 ? "Medium" : "Low";

  const sparkValues = useMemo(() => {
    const values = riskHistory.length > 0 ? riskHistory.map((score) => Math.round(score * 100)) : [14, 16, 18, 20, 24, 22, 26, 28];
    return values.slice(-8);
  }, [riskHistory]);

  const recommendation = latestMemory?.summary
    ? latestMemory.summary
    : density > 0.55
      ? "Deploy 3 responders to Gate B and open a secondary crowd corridor."
      : "Maintain patrol coverage around the highest-risk concourse and monitor queue buildup.";

  return (
    <Card className="overflow-hidden border-border/60 bg-white/90 shadow-sm backdrop-blur transition-shadow hover:shadow-lg dark:bg-card/90">
      <div className="absolute inset-0 bg-gradient-to-br from-black/5 via-transparent to-transparent pointer-events-none" />
      <CardHeader className="border-b border-border/50 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-tight text-foreground">
            <BrainCircuit className="h-4 w-4 text-foreground" />
            AI Recommendation
          </CardTitle>
          <Badge className="rounded-full border-border/60 bg-background px-2.5 py-0 text-[10px] uppercase tracking-[0.18em] text-foreground">
            Predictive active
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 px-4 py-4">
        <div className="flex items-start gap-4">
          <ConfidenceRing confidence={confidence} />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground" title="AI automatically processes raw data to reduce cognitive overload for human dispatchers">
              Recommended action (Cognitive Load Reduced)
            </div>
            <div className="text-sm font-semibold leading-snug text-foreground">{recommendation}</div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="rounded-full border-border/60 bg-background px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-foreground">
                Estimated impact {estimatedImpact}
              </Badge>
              <Badge variant="outline" className="rounded-full border-border/60 bg-muted px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Crowd surge in {predictedMinutes} min
              </Badge>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {[
            { label: "Confidence", value: `${confidence}%` },
            { label: "Impact", value: estimatedImpact },
            { label: "Route", value: "Gate B" },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{item.label}</div>
              <div className="mt-1 text-sm font-semibold text-foreground">{item.value}</div>
            </div>
          ))}
        </div>

        <div className="space-y-2 rounded-xl border border-border/60 bg-muted/30 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Reasoning</span>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="space-y-1.5 text-[12px] leading-relaxed text-muted-foreground">
            <div>• Crowd density is rising in the highest-pressure sector.</div>
            <div>• Active incident volume is currently above the low-risk baseline.</div>
            <div>• Historical pattern memory suggests proactive route opening reduces dwell time.</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5" />
            Risk trajectory
          </div>
          <div className="flex items-end gap-1 h-16 rounded-xl border border-border/60 bg-muted/20 p-2">
            {sparkValues.map((value, index) => (
              <div
                key={index}
                className={cn(
                  "w-full rounded-t-md transition-all duration-500",
                  value > 70 ? "bg-slate-950" : value > 40 ? "bg-slate-700/80" : "bg-slate-500/60"
                )}
                style={{ height: `${Math.max(value, 8)}%` }}
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}