import { Activity, Bell, Settings } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./ThemeToggle";

export function TopNav() {
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
        <ThemeToggle />
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground relative">
          <Bell className="h-4 w-4" />
          {/* Animated red dot for unread high-priority notifications */}
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-destructive animate-pulse" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
