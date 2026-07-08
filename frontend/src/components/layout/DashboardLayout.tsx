import { ReactNode } from "react";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground selection:bg-primary/30">
      <TopNav />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {/* Main content goes here, which will include the Map, Insight Panels, etc. */}
          {children}
        </main>
      </div>
    </div>
  );
}
