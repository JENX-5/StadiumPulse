import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";

import { useAppStore } from "@/store/useAppStore";
import { riskApi, zonesApi } from "@/services/api";

export const ZONE_CENTERS: Record<string, { cx: number, cy: number, r: number }> = {
  "North Concourse": { cx: 400, cy: 100, r: 150 },
  "South Concourse": { cx: 400, cy: 500, r: 150 },
  "Main Entrance": { cx: 100, cy: 300, r: 120 },
  "Section 114": { cx: 700, cy: 300, r: 120 },
  "VIP Suites": { cx: 400, cy: 300, r: 140 },
};

export function RiskHeatmap() {
  const { venueId } = useAppStore();
  
  const { data: zones = [] } = useQuery({
    queryKey: ["zones", venueId],
    queryFn: () => venueId ? zonesApi.list(venueId) : Promise.resolve([]),
    enabled: !!venueId,
  });

  const { data: heatmapData = {} } = useQuery({
    queryKey: ["risk-heatmap", venueId],
    queryFn: () => riskApi.getHeatmap(venueId),
    enabled: !!venueId,
    refetchInterval: 5000,
  });

  return (
    <div className="absolute inset-0 pointer-events-none mix-blend-screen opacity-90 flex items-center justify-center z-10">
      <svg viewBox="0 0 800 600" className="w-[85%] h-[85%]">
        <defs>
          <filter id="heatmap-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="40" />
          </filter>
        </defs>
        {zones.map((zone) => {
          const center = ZONE_CENTERS[zone.name];
          if (!center) return null;
          
          const risk = heatmapData[zone.id] || 0;
          
          let color = "rgba(59, 130, 246, 0.1)"; // Idle / Safe (Blue)
          if (risk >= 70) color = "rgba(239, 68, 68, 0.8)"; // Critical (Red)
          else if (risk >= 40) color = "rgba(234, 179, 8, 0.6)"; // Warning (Yellow)
          else if (risk > 10) color = "rgba(34, 197, 94, 0.3)"; // Active (Green)

          const radiusScale = 1 + (risk / 100) * 0.4;

          return (
            <motion.circle
              key={zone.id}
              cx={center.cx}
              cy={center.cy}
              r={center.r * radiusScale}
              fill={color}
              filter="url(#heatmap-blur)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, r: center.r * radiusScale, fill: color }}
              transition={{ duration: 1.5, ease: "easeInOut" }}
            />
          );
        })}
      </svg>
    </div>
  );
}
