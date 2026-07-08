import { AlertTriangle, Bot, History, Map, Users } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { icon: Map, label: "Live Map", active: true },
  { icon: AlertTriangle, label: "Incidents", active: false },
  { icon: Users, label: "Resources", active: false },
  { icon: Bot, label: "AI Agents", active: false },
  { icon: History, label: "Timeline", active: false },
];

export function Sidebar() {
  return (
    <aside className="w-16 lg:w-56 border-r border-border/40 bg-card/20 flex flex-col items-center lg:items-start py-4 shrink-0">
      <nav className="flex flex-col gap-1.5 w-full px-2 lg:px-3">
        {navItems.map((item) => (
          <button
            key={item.label}
            className={cn(
              "flex items-center justify-center lg:justify-start gap-3 w-full p-2.5 rounded-md transition-colors group relative",
              item.active 
                ? "bg-primary/10 text-primary" 
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            <item.icon className={cn("h-4 w-4 shrink-0", item.active && "text-primary")} />
            <span className="hidden lg:block text-sm font-medium">{item.label}</span>
            
            {/* Active indicator bar */}
            {item.active && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-primary rounded-r-full" />
            )}
          </button>
        ))}
      </nav>
    </aside>
  );
}
