"use client";

import { Activity, Bell, LogOut, Moon, Palette, Settings, Sun, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/store/useAuthStore";
import { useAppStore, TimelineEvent } from "@/store/useAppStore";
import { ThemeToggle } from "./ThemeToggle";

export function TopNav() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, logout } = useAuthStore();
  const { timelineEvents } = useAppStore();

  const [notifOpen, setNotifOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) setSettingsOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

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
    <header className="h-14 flex shrink-0 items-center justify-between px-4 lg:px-6 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50">
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
          <Activity className="h-4 w-4 text-primary" />
        </div>
        <span className="font-semibold text-base tracking-tight text-foreground">
          StadiumPulse
        </span>
        <span className="hidden sm:inline-flex ml-2 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] uppercase font-bold tracking-wider">
          Mission Control
        </span>
      </div>
      
      <div className="flex items-center gap-1">
        {user && (
          <div className="hidden sm:flex items-center gap-2 mr-1 pr-3 border-r border-border/40">
            <span className="text-xs font-medium text-foreground">{user.full_name}</span>
            <span className="px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground text-[10px] uppercase font-bold tracking-wide">
              {user.role}
            </span>
          </div>
        )}
        <ThemeToggle />

        {/* Notifications Bell */}
        <div ref={notifRef} className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground relative"
            onClick={() => { setNotifOpen(!notifOpen); setSettingsOpen(false); }}
          >
            <Bell className="h-4 w-4" />
            {recentEvents.length > 0 && (
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-destructive animate-pulse" />
            )}
          </Button>

          {notifOpen && (
            <div className="absolute right-0 top-10 w-72 rounded-lg border border-border bg-card shadow-2xl z-50 overflow-hidden">
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
                    <div key={event.id} className="px-3 py-2 border-b border-border/20 hover:bg-muted/20 transition-colors">
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
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            onClick={() => { setSettingsOpen(!settingsOpen); setNotifOpen(false); }}
          >
            <Settings className="h-4 w-4" />
          </Button>

          {settingsOpen && (
            <div className="absolute right-0 top-10 w-56 rounded-lg border border-border bg-card shadow-2xl z-50 overflow-hidden">
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
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          onClick={handleLogout}
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
