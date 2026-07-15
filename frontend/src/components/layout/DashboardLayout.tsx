import { ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex h-[100dvh] w-full flex-col overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <a 
        href="#main-content" 
        className="absolute left-1/2 top-4 -translate-x-1/2 -translate-y-24 rounded-md bg-primary px-4 py-2 text-sm font-bold text-primary-foreground shadow-lg transition-transform focus:translate-y-0 z-50"
      >
        Skip to main content
      </a>
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 h-80 w-[46rem] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-[-10rem] right-[-6rem] h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.04),_transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_20%)] dark:bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.05),_transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_20%)]" />
      </div>
      <TopNav />
      <div className="relative flex flex-1 min-h-0 overflow-hidden">
        <Sidebar />
        <main id="main-content" tabIndex={-1} className="relative flex min-w-0 min-h-0 flex-1 flex-col overflow-hidden focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}
