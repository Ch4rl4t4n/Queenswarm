"use client";

import type { CSSProperties } from "react";

import type { AgentRow } from "@/lib/hive-types";

const STATUS_RING: Record<string, string> = {
  IDLE: "ring-cyan/50 shadow-[0_0_14px_rgba(0,255,255,0.35)]",
  RUNNING: "ring-[#FFB800]/60 shadow-[0_0_20px_rgba(255,184,0,0.55)]",
  BUSY: "ring-[#FFB800]/55 shadow-[0_0_18px_rgba(255,184,0,0.45)]",
  ERROR: "ring-alert/55 shadow-[0_0_18px_rgba(255,0,170,0.45)]",
  OFFLINE: "ring-slate-600/50 opacity-65",
};

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

interface AgentHexCardProps {
  agent: AgentRow;
}

export function AgentHexCard({ agent }: AgentHexCardProps) {
  const glowPx = Math.min(48, 10 + Number(agent.pollen_points) * 2.8);
  const ring = STATUS_RING[agent.status] ?? STATUS_RING.IDLE;

  return (
    <div
      style={{ "--hive-glow": `${glowPx}px` } as CSSProperties}
      className={`group relative flex flex-col gap-2 p-6 text-center hive-hex bg-[#090918] bg-gradient-to-br from-[#0d1028] via-[#080812] to-[#050510] ${ring}`}
    >
      <div
        className="pointer-events-none absolute inset-0 hive-hex opacity-80 blur-2xl duration-700 group-hover:opacity-100"
        style={{
          boxShadow: `inset 0 0 ${glowPx}px rgba(255, 184, 0, 0.22)`,
        }}
      />
      <p className="font-[family-name:var(--font-space-grotesk)] text-sm tracking-wide text-data">
        {statusLabel(agent.status)}
      </p>
      <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-pollen">
        {agent.name}
      </h3>
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase text-muted-foreground">
        {agent.role.replaceAll("_", " ")}
      </p>
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#00FF88]">
        pollen {Number(agent.pollen_points).toFixed(2)}
      </p>
    </div>
  );
}
