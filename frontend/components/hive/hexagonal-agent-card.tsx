"use client";

import Link from "next/link";
import { BotIcon } from "lucide-react";

import { StatusIndicator, type StatusTone } from "@/components/ui/status-indicator";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function agentTone(status: string): StatusTone {
  const u = status.toUpperCase();
  if (u === "RUNNING" || u === "BUSY") {
    return "online";
  }
  if (u === "ERROR") {
    return "error";
  }
  if (u === "OFFLINE") {
    return "offline";
  }
  return "idle";
}

interface HexagonalAgentCardProps {
  agent: AgentRow;
  className?: string;
}

/** Hex-accent agent tile — pollen scales outer glow; status lamp maps hive enums. */
export function HexagonalAgentCard({ agent, className }: HexagonalAgentCardProps) {
  const glowPx = Math.min(52, 8 + Number(agent.pollen_points) * 2.4);
  const tone = agentTone(agent.status);
  const score =
    agent.performance_score !== undefined && agent.performance_score !== null
      ? `${(Number(agent.performance_score) <= 1 ? Number(agent.performance_score) * 100 : Number(agent.performance_score)).toFixed(0)}%`
      : "—";

  const roleLabel = agent.role.replaceAll("_", " ");

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={cn(
        "relative block rounded-2xl outline-none ring-offset-2 ring-offset-hive-bg focus-visible:ring-2 focus-visible:ring-pollen",
        className,
      )}
    >
      <div
        style={{ boxShadow: `0 0 ${glowPx}px rgba(255, 184, 0, 0.18)` }}
        className="relative flex flex-col gap-2 rounded-2xl border border-cyan/20 bg-gradient-to-b from-[#101228]/95 to-[#050510] p-3 text-left transition hover:border-pollen/35 sm:gap-3 sm:p-4"
      >
      <div className="flex items-start justify-between gap-2">
        <div
          className="hive-hex relative flex h-12 w-12 shrink-0 items-center justify-center border-[6px] border-data/35 bg-[#0a0c1c] ring-[4px] ring-data/30 md:h-14 md:w-14"
          aria-hidden
        >
          <BotIcon className="h-6 w-6 text-data md:h-7 md:w-7" />
          <div className="absolute -right-0.5 -top-0.5 rounded-full bg-[#050510] p-0.5">
            <StatusIndicator tone={tone} pulse={tone === "online"} aria-label={`status ${tone}`} />
          </div>
        </div>
      </div>
      <div className="space-y-1">
        <h3 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen sm:text-base">{agent.name}</h3>
        <p className="font-[family-name:var(--font-poppins)] text-[11px] uppercase tracking-wide text-cyan/75">
          {roleLabel}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-2 font-[family-name:var(--font-poppins)] text-xs">
        <div>
          <dt className="text-muted-foreground">pollen</dt>
          <dd className="text-pollen">{Number(agent.pollen_points).toFixed(2)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">score</dt>
          <dd className="text-data">{score}</dd>
        </div>
      </dl>
      </div>
    </Link>
  );
}
