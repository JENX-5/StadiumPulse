import { AlertTriangle, Clock, Users } from "lucide-react";

import { Card } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";

export function KPICards() {
  const { liveState } = useAppStore();

  const density = liveState?.global_crowd_density ?? 0.15;
  const activeIncidents = liveState?.active_incidents ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 lg:gap-4 mb-4">
      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Active Incidents
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {activeIncidents}
        </div>
      </Card>

      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <Users className="h-4 w-4 text-primary" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Crowd Density
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          {(density * 100).toFixed(1)}<span className="text-muted-foreground text-lg">%</span>
        </div>
      </Card>

      <Card className="p-4 bg-card/30 backdrop-blur border-border/40 shadow-sm transition-all hover:bg-card/50">
        <div className="flex items-center gap-2.5 text-muted-foreground mb-1.5">
          <Clock className="h-4 w-4 text-blue-500" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Response Time
          </span>
        </div>
        <div className="text-2xl font-medium tracking-tight text-foreground">
          2<span className="text-muted-foreground text-sm">m</span> 14<span className="text-muted-foreground text-sm">s</span>
        </div>
      </Card>
    </div>
  );
}
