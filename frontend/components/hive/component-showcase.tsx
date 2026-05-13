"use client";

import confetti from "canvas-confetti";
import { BotIcon, DollarSignIcon, HexagonIcon, PartyPopperIcon, ZapIcon } from "lucide-react";

import { AgentGrid } from "@/components/hive/agent-grid";
import { DataCard } from "@/components/hive/data-card";
import { HexagonalAgentCard } from "@/components/hive/hexagonal-agent-card";
import { NeonButton } from "@/components/ui/neon-button";
import { ProgressBar } from "@/components/ui/progress-bar";
import { StatusIndicator } from "@/components/ui/status-indicator";
import type { AgentRow } from "@/lib/hive-types";

const DEMO_AGENT: AgentRow = {
  id: "demo-1",
  name: "Scout-01",
  role: "SCRAPER",
  status: "RUNNING",
  pollen_points: 42.5,
  performance_score: 0.91,
};

/** Interactive catalog from the Figma design manual (tokens + motion demos). */
export function ComponentShowcase() {
  return (
    <div className="space-y-12 pb-16">
      <header className="space-y-2">
        <p className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.28em] text-cyan/70">
          queenswarm · neon-dark kit
        </p>
        <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-semibold text-pollen">
          Component showcase
        </h1>
        <p className="max-w-2xl font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
          Mirrors the Figma manual: status lamps, neon CTAs, shimmer progress, metric tiles, and hive agent tiles.
        </p>
      </header>

      <section className="space-y-4 rounded-2xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-data">StatusIndicator</h2>
        <div className="flex flex-wrap gap-6">
          <StatusIndicator tone="online" label="Online" />
          <StatusIndicator tone="idle" label="Idle" pulse={false} />
          <StatusIndicator tone="error" label="Error" pulse={false} />
          <StatusIndicator tone="offline" label="Offline" pulse={false} />
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-data">NeonButton</h2>
        <div className="flex flex-wrap gap-3">
          <NeonButton variant="primary">Primary</NeonButton>
          <NeonButton variant="secondary">Secondary</NeonButton>
          <NeonButton variant="ghost">Ghost</NeonButton>
          <NeonButton variant="danger">Danger</NeonButton>
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-data">ProgressBar</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <ProgressBar variant="pollen" value={72} label="Pollen lane" />
          <ProgressBar variant="data" value={54} label="Data throughput" />
          <ProgressBar variant="success" value={88} label="Verification" />
          <ProgressBar variant="alert" value={33} label="Risk budget" />
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-data">DataCard</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <DataCard label="Total agents" value="128" icon={BotIcon} trendPercent={12} />
          <DataCard label="Active tasks" value="47" icon={ZapIcon} trendPercent={8} />
          <DataCard label="Today pollen" value="24.5K" icon={HexagonIcon} trendPercent={23} />
          <DataCard label="Current cost" value="$12.34" icon={DollarSignIcon} trendPercent={-4} />
        </div>
      </section>

      <section className="space-y-4 rounded-2xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-data">HexagonalAgentCard + AgentGrid</h2>
        <AgentGrid>
          <HexagonalAgentCard agent={DEMO_AGENT} />
          <HexagonalAgentCard agent={{ ...DEMO_AGENT, id: "2", name: "Eval-01", role: "EVALUATOR", status: "IDLE" }} />
          <HexagonalAgentCard agent={{ ...DEMO_AGENT, id: "3", name: "Sim-02", role: "SIMULATOR", status: "BUSY" }} />
          <HexagonalAgentCard agent={{ ...DEMO_AGENT, id: "4", name: "Rep-01", role: "REPORTER", status: "ERROR" }} />
        </AgentGrid>
      </section>

      <section className="rounded-2xl border border-success/25 bg-black/35 p-6">
        <NeonButton
          variant="secondary"
          type="button"
          className="uppercase tracking-[0.2em]"
          onClick={() =>
            confetti({
              particleCount: 220,
              spread: 90,
              startVelocity: 36,
              origin: { x: 0.5, y: 0.2 },
              colors: ["#FFB800", "#00FFFF", "#00FF88", "#FF00AA"],
            })
          }
        >
          <PartyPopperIcon className="h-4 w-4" aria-hidden />
          Confetti (canvas-confetti)
        </NeonButton>
      </section>
    </div>
  );
}
