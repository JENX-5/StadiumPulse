import { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { useAppStore } from "@/store/useAppStore";
import { riskApi } from "@/services/api";

export function RiskHeatmap() {
  const { liveState, venueId } = useAppStore();
  const [heatmapData, setHeatmapData] = useState<Record<string, number>>({});
  
  useEffect(() => {
    if (!venueId) return;
    
    // Poll the risk heatmap every 5 seconds
    const fetchHeatmap = () => {
      riskApi.getHeatmap(venueId)
        .then(data => setHeatmapData(data))
        .catch(err => console.error("Failed to fetch risk heatmap", err));
    };
    
    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 5000);
    return () => clearInterval(interval);
  }, [venueId]);

  // Use the max risk score from the backend for the severe hotspot
  const maxRisk = Object.values(heatmapData).length > 0 
    ? Math.max(...Object.values(heatmapData)) 
    : 0;

  // We use the real global_crowd_density from the operational engine if connected,
  // otherwise default to a low idle state.
  const density = liveState?.global_crowd_density ?? 0.15;
  const riskOpacity = Math.max(0.1, density);

  return (
    <div className="absolute inset-0 pointer-events-none mix-blend-screen opacity-70">
      {/* Primary baseline crowd density heatmap */}
      <motion.div
        animate={{
          opacity: [riskOpacity * 0.7, riskOpacity, riskOpacity * 0.7],
          scale: [0.97, 1, 0.97],
        }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[20%] left-[20%] w-[60%] h-[60%] rounded-[100%] bg-primary blur-[120px]"
      />

      {/* High Risk Hotspot (Driven by real backend risk scores) */}
      {maxRisk > 60 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 0.5, scale: 1 }}
          transition={{ duration: 2 }}
          className="absolute top-[25%] left-[55%] w-[30%] h-[40%] rounded-full bg-destructive blur-[90px]"
        />
      )}
    </div>
  );
}
