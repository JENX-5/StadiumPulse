"use client";

import { Bot, BrainCircuit, Eye, MessageSquare, Shield, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const AI_AGENTS = [
  {
    name: "Triage Agent",
    description: "Classifies incoming incident reports by severity and category using NLP.",
    status: "active",
    icon: MessageSquare,
    model: "Primary LLM",
    processedToday: 47,
    color: "text-foreground",
  },
  {
    name: "Risk Scoring Agent",
    description: "Continuously evaluates zone-level risk using crowd density, incident velocity, and weather.",
    status: "active",
    icon: Zap,
    model: "Real-time Pipeline",
    processedToday: 312,
    color: "text-foreground",
  },
  {
    name: "Dispatch Agent",
    description: "Recommends optimal resource dispatch based on proximity, availability, and incident priority.",
    status: "active",
    icon: Shield,
    model: "Primary LLM",
    processedToday: 23,
    color: "text-foreground",
  },
  {
    name: "Pattern Memory Agent",
    description: "Identifies recurring incident patterns across events for predictive analysis.",
    status: "idle",
    icon: BrainCircuit,
    model: "Escalation LLM",
    processedToday: 5,
    color: "text-foreground",
  },
  {
    name: "Crowd Monitor Agent",
    description: "Monitors crowd density sensors and triggers alerts when thresholds are exceeded.",
    status: "active",
    icon: Eye,
    model: "Sensor Pipeline",
    processedToday: 1024,
    color: "text-foreground",
  },
];

export function AgentsView() {
  return (
    <div className="flex flex-col h-full p-4 lg:p-6 gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">AI Agents</h1>
        <Badge className="bg-muted text-foreground border-border">
          {AI_AGENTS.filter((a) => a.status === "active").length}/{AI_AGENTS.length} Active
        </Badge>
      </div>

      <p className="text-sm text-muted-foreground">
        Autonomous agents that power real-time analysis, triage, and dispatch decisions.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 flex-1">
        {AI_AGENTS.map((agent) => (
          <Card
            key={agent.name}
            className="bg-card/50 border-border/40 hover:bg-card/80 transition-all p-5 flex flex-col gap-3"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-10 w-10 rounded-lg bg-muted/30 flex items-center justify-center ${agent.color}`}>
                  <agent.icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold">{agent.name}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{agent.model}</div>
                </div>
              </div>
              <Badge
                variant="outline"
                className={`text-[9px] uppercase tracking-wider rounded-sm px-1.5 ${
                  agent.status === "active"
                    ? "bg-muted text-foreground border-border"
                    : "bg-muted text-muted-foreground border-border"
                }`}
              >
                <span className={`inline-block h-1.5 w-1.5 rounded-full mr-1.5 ${
                  agent.status === "active" ? "bg-foreground animate-pulse" : "bg-muted-foreground"
                }`} />
                {agent.status}
              </Badge>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed flex-1">
              {agent.description}
            </p>

            <div className="border-t border-border/40 pt-3 flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Processed Today</span>
              <span className="text-sm font-mono font-medium text-foreground">
                {agent.processedToday.toLocaleString()}
              </span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
