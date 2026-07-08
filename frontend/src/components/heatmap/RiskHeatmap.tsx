import { motion } from "framer-motion";

import { useAppStore } from "@/store/useAppStore";

export function RiskHeatmap() {
  const { liveState } = useAppStore();

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

      {/* High Risk Hotspot (Simulated active incident or severe congestion) */}
      {density > 0.6 && (
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
