"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Bell, Clock3, LogOut, Palette, Radio, Settings, ShieldCheck, Sparkles, Wifi, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/useAuthStore";
import { useAppStore, TimelineEvent } from "@/store/useAppStore";
import { ThemeToggle } from "./ThemeToggle";
import { simulationApi } from "@/services/api";

export function TopNav() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, logout } = useAuthStore();
  const { timelineEvents, liveState } = useAppStore();
  const { data: simulationStatus } = useQuery({
    queryKey: ["simulation-status"],
    queryFn: () => simulationApi.getStatus(),
    refetchInterval: 4000,
  });

  const [notifOpen, setNotifOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [now, setNow] = useState(new Date());
  const notifRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) setSettingsOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("mousedown", handleClick);
    };
  }, []);

  const connectionLabel = liveState ? "Connected" : "Syncing";
  const aiActive = timelineEvents.some((event) => event.type.includes("agent"));
  const systemLabel = useMemo(() => {
    const crowd = liveState?.global_crowd_density ?? 0;
    const incidents = liveState?.active_incidents ?? 0;
    if (incidents >= 8 || crowd >= 0.78) return { label: "Critical", tone: "destructive" as const };
    if (incidents >= 4 || crowd >= 0.55) return { label: "Attention", tone: "warning" as const };
    return { label: "Nominal", tone: "success" as const };
  }, [liveState]);

  function handleLogout() {
    logout();
    queryClient.clear(); // Fix issue 17: clear stale data on logout
    router.push("/login");
  }

  // Recent notable events for the notification bell
  const recentEvents = timelineEvents
    .filter((e) => e.type.includes("incident") || e.type.includes("alert"))
    .slice(0, 5);

  return (
    <header className="relative z-50 border-b border-border/60 bg-white/85 backdrop-blur-xl dark:bg-slate-950/75">
      <div className="flex h-16 items-center justify-between gap-4 px-4 lg:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-inset ring-primary/10">
            <Activity className="h-4.5 w-4.5 text-foreground" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-semibold tracking-tight text-foreground lg:text-base">
                StadiumPulse
              </span>
              <span className="hidden sm:inline-flex rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
                Mission Control
              </span>
            </div>
            <div className="text-[11px] text-muted-foreground">AI-powered stadium operations for live events</div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {user && (
            <div className="hidden items-center gap-2 rounded-full border border-border/60 bg-background/70 px-3 py-1.5 sm:flex">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
                {user.full_name
                  .split(" ")
                  .map((part) => part[0])
                  .slice(0, 2)
                  .join("")}
              </span>
              <div className="min-w-0">
                <div className="truncate text-xs font-medium text-foreground">{user.full_name}</div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{user.role}</div>
              </div>
            </div>
          )}
          <div className="hidden sm:block">
            <ThemeToggle />
          </div>

        {/* Notifications Bell */}
        <div ref={notifRef} className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="relative h-9 w-9 rounded-xl text-muted-foreground hover:bg-muted/70 hover:text-foreground"
            onClick={() => { setNotifOpen(!notifOpen); setSettingsOpen(false); }}
          >
            <Bell className="h-4 w-4" />
            {recentEvents.length > 0 && (
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-destructive animate-pulse" />
            )}
          </Button>

          {notifOpen && (
            <div className="absolute right-0 top-11 w-80 overflow-hidden rounded-xl border border-border/70 bg-card/95 shadow-2xl shadow-black/20 backdrop-blur-xl z-50">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border/40 bg-muted/30">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Notifications</span>
                <button onClick={() => setNotifOpen(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {recentEvents.length === 0 ? (
                  <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                    No recent alerts. All clear.
                  </div>
                ) : (
                  recentEvents.map((event: TimelineEvent) => (
                    <div key={event.id} className="border-b border-border/20 px-3 py-2 transition-colors hover:bg-muted/20">
                      <div className="flex items-center justify-between mb-0.5">
                        <Badge variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm px-1">
                          {event.type}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate">
                        {event.payload ? JSON.stringify(event.payload).substring(0, 60) : "Event received"}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Settings Button */}
        <div ref={settingsRef} className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-xl text-muted-foreground hover:bg-muted/70 hover:text-foreground"
            onClick={() => { setSettingsOpen(!settingsOpen); setNotifOpen(false); }}
          >
            <Settings className="h-4 w-4" />
          </Button>

          {settingsOpen && (
            <div className="absolute right-0 top-11 w-60 overflow-hidden rounded-xl border border-border/70 bg-card/95 shadow-2xl shadow-black/20 backdrop-blur-xl z-50">
              <div className="px-3 py-2 border-b border-border/40 bg-muted/30">
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Settings</span>
              </div>
              <div className="p-2 space-y-1">
                <div className="flex items-center justify-between px-2 py-1.5 rounded text-xs text-muted-foreground">
                  <span className="flex items-center gap-2">
                    <Palette className="h-3.5 w-3.5" />
                    Theme
                  </span>
                  <ThemeToggle />
                </div>
                <div className="border-t border-border/40 my-1" />
                <div className="px-2 py-1.5 text-[11px] text-muted-foreground">
                  <span className="font-medium">Venue:</span> Demo Stadium
                </div>
                <div className="px-2 py-1.5 text-[11px] text-muted-foreground">
                  <span className="font-medium">Version:</span> 1.0.0-dev
                </div>
              </div>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-xl text-muted-foreground hover:bg-muted/70 hover:text-foreground"
          onClick={handleLogout}
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </Button>
        </div>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto border-t border-border/50 px-4 py-2.5 lg:px-6">
        <Badge variant="outline" className="rounded-full border-border/60 bg-background/70 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          <Clock3 className="mr-1.5 h-3 w-3" />
          {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </Badge>
        <Badge variant="outline" className="rounded-full border-border/60 bg-background/70 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          <Wifi className="mr-1.5 h-3 w-3" />
          {connectionLabel}
        </Badge>
        <Badge variant="outline" className="rounded-full border-border/60 bg-background/70 px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          <Sparkles className="mr-1.5 h-3 w-3" />
          {aiActive ? "AI active" : "AI monitoring"}
        </Badge>
        <Badge
          variant="outline"
          className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${
            simulationStatus?.is_running
              ? simulationStatus.is_paused
                ? "border-border/70 bg-muted/70 text-muted-foreground"
                : "border-border/70 bg-background text-foreground"
              : "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          }`}
        >
          <Radio className="mr-1.5 h-3 w-3" />
          {simulationStatus ? (simulationStatus.is_running ? (simulationStatus.is_paused ? "Simulation paused" : "Simulation running") : "Simulation stopped") : "Loading simulation"}
        </Badge>
        <Badge
          variant="outline"
          className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${
            systemLabel.tone === "success"
              ? "border-border/70 bg-background text-foreground"
              : systemLabel.tone === "warning"
                ? "border-border/70 bg-muted/70 text-muted-foreground"
                : "border-border/70 bg-muted text-foreground"
          }`}
        >
          <ShieldCheck className="mr-1.5 h-3 w-3" />
          {systemLabel.label} system health
        </Badge>
      </div>
    </header>
  );
}
