import { BrainCircuit, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";

export function AIInsightsPanel() {
  const { liveState } = useAppStore();
  
  const density = liveState?.global_crowd_density ?? 0.15;
  const isHighRisk = density > 0.6;

  return (
    <Card className="flex flex-col bg-primary/5 backdrop-blur-md border-primary/20 overflow-hidden relative shadow-2xl">
      {/* Decorative Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent pointer-events-none" />
      
      <CardHeader className="py-3 px-4 border-b border-primary/10 z-10">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 uppercase tracking-widest text-primary">
            <BrainCircuit className="h-4 w-4" />
            Predictive Insights
          </CardTitle>
          <div className="flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-4 z-10 flex flex-col gap-4">
        {/* Mock Forecast based on current operational density */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-bold text-muted-foreground">Crowd Forecast (T+15m)</span>
            <Badge variant="outline" className={`text-[9px] uppercase tracking-wider px-1.5 py-0 rounded-sm ${isHighRisk ? 'text-destructive border-destructive/50 bg-destructive/10' : 'text-primary border-primary/50 bg-primary/10'}`}>
              {isHighRisk ? 'Critical' : 'Stable'}
            </Badge>
          </div>
          
          <div className="text-sm leading-relaxed text-foreground/90">
            {isHighRisk 
              ? "Models indicate a 87% probability of severe congestion at Gate C in the next 15 minutes. Pre-emptive redirection of ingress traffic recommended."
              : "Flow rates remain optimal. Expected peak ingress will naturally decay over the next 30 minutes with no projected bottlenecks."}
          </div>
        </div>

        <div className="h-px w-full bg-primary/10" />

        <div className="space-y-2">
           <div className="flex items-center gap-2 text-xs uppercase tracking-wider font-bold text-muted-foreground">
             <TrendingUp className="h-3 w-3" /> Risk Trajectory
           </div>
           <div className="flex items-end gap-1 h-8">
             {/* Dummy mini sparkline */}
             {[40, 45, 42, 50, 55, 60, isHighRisk ? 85 : 58, isHighRisk ? 90 : 55].map((val, i) => (
               <div 
                 key={i} 
                 className={`w-full rounded-t-sm transition-all duration-500 ${val > 80 ? 'bg-destructive' : 'bg-primary/40'}`} 
                 style={{ height: `${val}%` }} 
               />
             ))}
           </div>
        </div>
      </CardContent>
    </Card>
  );
}
