
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ShieldAlert, HeartPulse, HardHat, UserSquare2 } from "lucide-react";

import { useAppStore } from "@/store/useAppStore";
import { incidentsApi, resourcesApi, zonesApi } from "@/services/api";
import { RiskHeatmap, ZONE_CENTERS } from "../heatmap/RiskHeatmap";

export function StadiumMap() {
  const { liveState, venueId } = useAppStore();

  const { data: zones = [], isLoading: zonesLoading, isError: zonesError } = useQuery({
    queryKey: ["zones", venueId],
    queryFn: () => venueId ? zonesApi.list(venueId) : Promise.resolve([]),
    enabled: !!venueId,
  });

  const { data: incidents = [] } = useQuery({
    queryKey: ["incidents", venueId],
    queryFn: () => venueId ? incidentsApi.listByVenue(venueId) : Promise.resolve([]),
    enabled: !!venueId,
    refetchInterval: 5000,
  });

  const { data: resources = [] } = useQuery({
    queryKey: ["resources", venueId],
    queryFn: () => venueId ? resourcesApi.list(venueId) : Promise.resolve([]),
    enabled: !!venueId,
    refetchInterval: 5000,
  });

  const zoneIdToCenter = new Map();
  zones.forEach(z => {
    const center = ZONE_CENTERS[z.name];
    if (center) zoneIdToCenter.set(z.id, center);
  });

  const getJitter = (id: string, index: number, radiusBase: number = 30) => {
    const hash = id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const angle = (hash + index * 45) * (Math.PI / 180);
    const radius = radiusBase + (hash % 30);
    return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
  };

  return (
    <div className="relative w-full h-full bg-card overflow-hidden rounded-xl border border-border/20 shadow-2xl flex items-center justify-center">
      <div 
        className="absolute inset-0 opacity-[0.04]" 
        style={{ 
          backgroundImage: "radial-gradient(circle at 2px 2px, currentColor 1px, transparent 0)", 
          backgroundSize: "32px 32px" 
        }}
      />

      {zonesLoading ? (
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-xs uppercase tracking-wider">Loading map data…</span>
        </div>
      ) : zonesError ? (
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <span className="text-sm">Failed to load map data.</span>
          <span className="text-xs">Check that the backend is running.</span>
        </div>
      ) : (
      <>
      <RiskHeatmap />
      
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
        <svg viewBox="0 0 800 600" className="w-[85%] h-[85%] text-primary" stroke="currentColor" fill="none">
           <rect x="50" y="50" width="700" height="500" rx="200" strokeWidth="1.5" className="opacity-40" />
           <rect x="100" y="100" width="600" height="400" rx="150" strokeWidth="1" strokeDasharray="4 6" className="opacity-40" />
           <rect x="150" y="150" width="500" height="300" rx="100" strokeWidth="0.5" className="opacity-40" />
           
           <rect x="250" y="200" width="300" height="200" rx="10" strokeWidth="2" fill="currentColor" fillOpacity="0.05" className="opacity-40" />
           <circle cx="400" cy="300" r="40" strokeWidth="1" className="opacity-40" />
           <line x1="400" y1="200" x2="400" y2="400" strokeWidth="1" className="opacity-40" />
           
           <line x1="50" y1="300" x2="150" y2="300" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
           <line x1="650" y1="300" x2="750" y2="300" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
           <line x1="400" y1="50" x2="400" y2="150" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />
           <line x1="400" y1="450" x2="400" y2="550" strokeWidth="1" strokeDasharray="2 4" className="opacity-40" />

           {/* Plot Active Incidents */}
           {incidents.filter(i => i.status !== "RESOLVED" && i.status !== "CLOSED").map((incident, i) => {
             if (!incident.zone_id) return null;
             const center = zoneIdToCenter.get(incident.zone_id);
             if (!center) return null;
             const jitter = getJitter(incident.id, i, 40);
             const x = center.cx + jitter.x;
             const y = center.cy + jitter.y;
             
             return (
               <g key={incident.id} transform={`translate(${x - 16}, ${y - 16})`}>
                 <foreignObject width="150" height="150" className="overflow-visible pointer-events-auto">
                   <div className="relative group cursor-pointer w-8 h-8">
                     <div className="absolute -inset-1 bg-destructive/30 rounded-full animate-ping" />
                     <div className="relative bg-destructive text-destructive-foreground p-1.5 rounded-full shadow-lg border-2 border-red-400">
                       <AlertCircle className="w-4 h-4" />
                     </div>
                     <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bottom-full mb-2 left-1/2 -translate-x-1/2 whitespace-nowrap bg-black text-white text-[11px] font-medium px-3 py-1.5 rounded shadow-xl border border-white/10 pointer-events-none z-50">
                       <span className="text-destructive font-bold mr-1">[{incident.severity}]</span> {incident.raw_text.substring(0, 40)}{incident.raw_text.length > 40 ? '...' : ''}
                     </div>
                   </div>
                 </foreignObject>
               </g>
             );
           })}

           {/* Plot Resources */}
           {resources.map((resource, i) => {
             if (!resource.current_zone_id) return null;
             const center = zoneIdToCenter.get(resource.current_zone_id);
             if (!center) return null;
             const jitter = getJitter(resource.id, i + 13, 20);
             const x = center.cx + jitter.x;
             const y = center.cy + jitter.y;
             
             let Icon = ShieldAlert;
             let colorClass = "bg-blue-500 border-blue-300";
             if (resource.resource_type === "medical") { Icon = HeartPulse; colorClass = "bg-green-500 border-green-300"; }
             else if (resource.resource_type === "maintenance" || resource.resource_type === "cleaning") { Icon = HardHat; colorClass = "bg-orange-500 border-orange-300"; }
             else if (resource.resource_type === "volunteer") { Icon = UserSquare2; colorClass = "bg-purple-500 border-purple-300"; }

             return (
               <g key={resource.id} transform={`translate(${x - 14}, ${y - 14})`}>
                 <foreignObject width="100" height="100" className="overflow-visible pointer-events-auto">
                   <div className="relative group cursor-pointer w-7 h-7">
                     <div className={`relative text-white p-1.5 rounded-full shadow-md border ${colorClass}`}>
                       <Icon className="w-3.5 h-3.5" />
                     </div>
                     <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap bg-black text-white text-[10px] px-2 py-1 rounded shadow-lg pointer-events-none z-50">
                       {resource.label}
                     </div>
                   </div>
                 </foreignObject>
               </g>
             );
           })}
        </svg>
      </div>
      
      <div className="absolute top-6 left-6 z-30">
        <div className="px-3 py-1.5 rounded-full bg-primary/10 text-primary text-[11px] font-bold tracking-widest border border-primary/20 flex items-center gap-2.5 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          {liveState ? "LIVE DATA SYNCED" : "AWAITING TELEMETRY..."}
        </div>
      </div>
      </>
      )}
    </div>
  );
}
