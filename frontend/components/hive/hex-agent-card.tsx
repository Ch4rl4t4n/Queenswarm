"use client";

import Link from "next/link";
import type { CSSProperties } from "react";

import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

const SWARM_HEX: Record<string, string> = {
  scout: "#00E5FF",
  eval: "#FFB800",
  sim: "#FF00AA",
  action: "#00FF88",
};

const STATUS_COLORS: Record<"live" | "idle" | "paused" | "error", string> = {
  live: "#00FF88",
  idle: "#FFB800",
  paused: "#FF3366",
  error: "#FF3366",
};

export function swarmKeyFromAgent(agent: AgentRow): keyof typeof SWARM_HEX {
  const tier = (agent.hive_tier ?? "").toLowerCase();
  if (tier === "orchestrator") {
    return "eval";
  }
  const blob = `${agent.swarm_purpose ?? ""} ${agent.swarm_name ?? ""} ${agent.role ?? ""}`.toLowerCase();
  if (blob.includes("scout")) return "scout";
  if (blob.includes("eval")) return "eval";
  if (blob.includes("sim")) return "sim";
  if (blob.includes("action")) return "action";
  return "scout";
}

function statusVisual(status: string): { tone: keyof typeof STATUS_COLORS; pulse: boolean } {
  const u = status.toUpperCase();
  if (u === "RUNNING" || u === "BUSY") return { tone: "live", pulse: true };
  if (u === "PAUSED") return { tone: "paused", pulse: false };
  if (u === "ERROR" || u === "OFFLINE") return { tone: "error", pulse: false };
  return { tone: "idle", pulse: false };
}

function formatRole(role: string): string {
  const cleaned = role.replace(/_/g, " ").trim();
  if (!cleaned) return "WorkerBee";
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function pctScore(s: number | undefined): number {
  if (s === undefined || Number.isNaN(s)) return 0;
  return Math.round(Math.min(1, Math.max(0, s)) * 100);
}

function pollenDisplay(points: number): string {
  const n = Number(points) || 0;
  if (n > 999) return `${(n / 1000).toFixed(1)}k`;
  return n.toFixed(n >= 100 ? 0 : 1);
}

interface HexAgentCardProps {
  agent: AgentRow;
  onClick?: () => void;
  /** Navigation target — renders `<Link>` with `.qs-hex` sizing */
  href?: string;
  showPerformance?: boolean;
  renderAsDiv?: boolean;
  className?: string;
}

/**
 * Canonical 136×156 agent hex (.qs-hex) shared by dashboard roster and agents explorer.
 */
export function HexAgentCard({
  agent,
  onClick,
  href,
  showPerformance = false,
  renderAsDiv = false,
  className,
}: HexAgentCardProps): JSX.Element {
  const swarm = swarmKeyFromAgent(agent);
  const color = SWARM_HEX[swarm] ?? SWARM_HEX.scout;
  const sv = statusVisual(agent.status ?? "");
  const statusColor = STATUS_COLORS[sv.tone];
  const pollenVal = pollenDisplay(agent.pollen_points ?? 0);
  const scoreP = pctScore(agent.performance_score);
  const idle = agent.status.toUpperCase() === "IDLE";

  const surface: CSSProperties = {
    background: "var(--qs-surface-2)",
    outline: `2px solid ${color}40`,
    outlineOffset: "-2px",
    boxShadow: sv.pulse ? `0 0 24px ${color}33` : "none",
  };

  const inner = (
    <div className="qs-hex__inner">
      <div
        className={cn("qs-hex__dot", sv.pulse && "qs-pulse")}
        style={{
          background: statusColor,
          boxShadow: sv.pulse ? `0 0 6px ${statusColor}` : "none",
        }}
      />
      <div className="qs-hex__name">{agent.name}</div>
      <div className="qs-hex__role">{formatRole(agent.role)}</div>
      <div className="qs-hex__pollen" style={{ color }}>
        ◈ {pollenVal}
      </div>
      {showPerformance && scoreP > 0 ? (
        <div className="mt-0.5 h-1 w-[90px] max-w-full overflow-hidden rounded-full bg-black/55">
          <div className="h-full rounded-full" style={{ width: `${scoreP}%`, backgroundColor: color }} />
        </div>
      ) : null}
    </div>
  );

  if (href) {
    return (
      <Link href={href} prefetch={false} className={cn("qs-hex", idle && "opacity-95", className)} style={surface}>
        {inner}
      </Link>
    );
  }

  if (renderAsDiv) {
    return (
      <div className={cn("qs-hex", idle && "opacity-90", className)} style={surface}>
        {inner}
      </div>
    );
  }

  return (
    <button
      type="button"
      className={cn("qs-hex", idle && "brightness-[0.94]", className)}
      style={surface}
      onClick={onClick}
    >
      {inner}
    </button>
  );
}
