"use client";

import { Hexagon } from "lucide-react";

import type { AgentsSwarmFilter } from "@/lib/agent-hive-lane";
import { agentListLane, laneTabLabel, laneTheme, roleDisplayName } from "@/lib/agents-list-presenters";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export interface AgentListRowProps {
  readonly agent: AgentRow;
  readonly onActivate: (agent: AgentRow) => void;
}

function formatPollen(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(1)}M`;
  }
  if (n >= 1000) {
    return `${(n / 1000).toFixed(1)}K`;
  }
  return String(Math.round(n * 10) / 10);
}

function pctScore(s: number | undefined): number {
  if (s === undefined || Number.isNaN(s)) {
    return 0;
  }
  return Math.round(Math.min(1, Math.max(0, s)) * 100);
}

function pctScoreDisplay(s: number | undefined): string {
  if (s === undefined || Number.isNaN(s)) {
    return "—";
  }
  return `${pctScore(s)}%`;
}

function statusDotClass(status: string): string {
  const u = status.toUpperCase();
  if (u === "RUNNING") {
    return "bg-cyan shadow-[0_0_8px_rgb(0_255_255/0.75)]";
  }
  if (u === "IDLE") {
    return "bg-zinc-400";
  }
  if (u === "PAUSED") {
    return "bg-alert";
  }
  if (u === "OFFLINE") {
    return "bg-zinc-500 ring-1 ring-zinc-400/35";
  }
  if (u === "ERROR") {
    return "bg-danger";
  }
  return "bg-zinc-600";
}

function agentStatusLine(agent: AgentRow): string {
  const t = (agent.current_task_title ?? "").trim();
  if (t) {
    return t;
  }
  const u = agent.status.toUpperCase();
  if (u === "RUNNING") {
    return "Working on task…";
  }
  if (u === "ERROR") {
    return "Error — needs attention";
  }
  if (u === "PAUSED") {
    return "Paused";
  }
  if (u === "OFFLINE") {
    return "Inactive (offline)";
  }
  return "Waiting for handoff";
}

/** Single scanable roster row for list view (shared by static + virtual lists). */
export function AgentListRow({ agent, onActivate }: AgentListRowProps): JSX.Element {
  const lane = agentListLane(agent);
  const theme = laneTheme(lane === "queen" ? "queen" : lane, agent);
  const err = agent.status.toUpperCase() === "ERROR";
  const offline = agent.status.toUpperCase() === "OFFLINE";
  const scoreP = pctScore(agent.performance_score);
  const laneLabel =
    lane === "queen" ? "Queen" : laneTabLabel(lane as Exclude<AgentsSwarmFilter, "all">);

  return (
    <div
      className={cn(
        "flex overflow-hidden rounded-2xl qs-rim bg-black/40",
        offline && "opacity-[0.78] saturate-[0.42]",
      )}
    >
      <div className={cn("w-1 shrink-0", offline ? "bg-zinc-600/85" : theme.listBar)} aria-hidden />
      <button
        type="button"
        onClick={() => onActivate(agent)}
        className="flex min-w-0 flex-1 flex-col gap-3 px-4 py-3 text-left transition hover:bg-white/[0.03] sm:flex-row sm:items-center sm:gap-6"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("h-2 w-2 shrink-0 rounded-full", statusDotClass(agent.status))} aria-hidden />
            <span className="font-[family-name:var(--font-poppins)] text-sm font-bold text-[#fafafa]">
              {agent.name}
            </span>
            <span className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
              {roleDisplayName(agent.role)}
            </span>
            <span className={cn("rounded-full border px-2 py-0.5 qs-chip uppercase", theme.pillClass)}>
              {laneLabel}
            </span>
          </div>
          <p className="mt-1.5 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">{agentStatusLine(agent)}</p>
        </div>
        <div className="flex shrink-0 flex-col gap-2 sm:w-40">
          <div>
            <div className="flex items-center justify-between qs-meta-label text-zinc-500">
              <span>Score</span>
              <span className={cn(err ? "text-danger" : theme.scoreText)}>{pctScoreDisplay(agent.performance_score)}</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-black/60">
              <div className={cn("h-full rounded-full", theme.barBg)} style={{ width: `${scoreP}%` }} />
            </div>
          </div>
          <div className="flex items-center gap-1.5 font-[family-name:var(--font-poppins)] text-xs tabular-nums text-pollen">
            <Hexagon className="h-3.5 w-3.5 text-pollen/90" aria-hidden />
            {formatPollen(agent.pollen_points ?? 0)}
          </div>
        </div>
      </button>
    </div>
  );
}
