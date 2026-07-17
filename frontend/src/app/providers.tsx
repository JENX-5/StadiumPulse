"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  // Initialize QueryClient lazily to ensure it is created once per session
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10 * 1000, // Data stays fresh for 10 seconds before background refetch
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {/* `reducedMotion="user"` makes every `motion.*` component in the app
          respect the OS-level prefers-reduced-motion setting automatically
          (disabling transform/layout animation, keeping opacity fades) --
          a single provider-level fix rather than touching every animated
          component individually (CommandCenterDashboard, StadiumMap,
          KPICards, RiskHeatmap, Sidebar all use motion.* directly). */}
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </QueryClientProvider>
  );
}
