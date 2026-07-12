import { motion } from "framer-motion";

import { useAppStore } from "@/store/useAppStore";
import { RiskHeatmap } from "../heatmap/RiskHeatmap";

export function StadiumMap() {
  const { liveState } = useAppStore();

  return (
    <div className="relative w-full h-full bg-card overflow-hidden rounded-xl border border-border/20 shadow-2xl flex items-center justify-center">
      {/* Subtle Tech Grid Background */}
      <div 
        className="absolute inset-0 opacity-[0.04]" 
        style={{ 
          backgroundImage: "radial-gradient(circle at 2px 2px, white 1px, transparent 0)", 
          backgroundSize: "32px 32px" 
        }}
      />
      
      {/* Dynamic Heatmap Layer */}
      <RiskHeatmap />
      
      {/* Vector Stadium Structure */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <svg viewBox="0 0 800 600" className="w-[85%] h-[85%] opacity-40 text-primary" stroke="currentColor" fill="none">
           {/* Outer Concourse */}
           <rect x="50" y="50" width="700" height="500" rx="200" strokeWidth="1.5" />
           <rect x="100" y="100" width="600" height="400" rx="150" strokeWidth="1" strokeDasharray="4 6" />
           <rect x="150" y="150" width="500" height="300" rx="100" strokeWidth="0.5" />
           
           {/* Central Pitch/Field */}
           <rect x="250" y="200" width="300" height="200" rx="10" strokeWidth="2" fill="currentColor" fillOpacity="0.05" />
           <circle cx="400" cy="300" r="40" strokeWidth="1" />
           <line x1="400" y1="200" x2="400" y2="400" strokeWidth="1" />
           
           {/* Zones Demarcations */}
           <line x1="50" y1="300" x2="150" y2="300" strokeWidth="1" strokeDasharray="2 4" />
           <line x1="650" y1="300" x2="750" y2="300" strokeWidth="1" strokeDasharray="2 4" />
           <line x1="400" y1="50" x2="400" y2="150" strokeWidth="1" strokeDasharray="2 4" />
           <line x1="400" y1="450" x2="400" y2="550" strokeWidth="1" strokeDasharray="2 4" />
        </svg>
      </div>
      
      {/* Live State Connection Status */}
      <div className="absolute top-6 left-6">
        <div className="px-3 py-1.5 rounded-full bg-primary/10 text-primary text-[11px] font-bold tracking-widest border border-primary/20 flex items-center gap-2.5 backdrop-blur-md">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          {liveState ? "LIVE DATA SYNCED" : "AWAITING TELEMETRY..."}
        </div>
      </div>
    </div>
  );
}
