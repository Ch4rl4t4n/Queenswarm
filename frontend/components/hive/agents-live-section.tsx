"use client";

import Link from "next/link";
import { Hexagon, LayoutGrid, List, Play, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import { HexAgentCard } from "@/components/hive/hex-agent-card";
import type { AgentsSwarmFilter, AgentHiveLane } from "@/lib/agent-hive-lane";
import { isQueenAgent } from "@/lib/agent-hive-lane";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export type { AgentsSwarmFilter, AgentHiveLane } from "@/lib/agent-hive-lane";

type ViewMode = "grid" | "list";

function filledHiveId(value: unknown): boolean {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

function hasSubSwarmId(agent: AgentRow): boolean {
  return filledHiveId(agent.sub_swarm_id);
}

function rawSwarmHints(agent: AgentRow): string {
  const parts = [agent.swarm_type, agent.swarm?.name, agent.swarm_name, agent.swarm_purpose].filter(Boolean);
  return parts.join(" ").toLowerCase();
}

/**
 * Roster grouping for pills (workers only). ``unassigned`` when ``sub_swarm_id`` absent or swarm kind unknown.
 *
 * Phase R: never infer assignment from ``swarm_id`` alone — only ``sub_swarm_id`` marks placement.
 */
function workerSwarmPillBucket(agent: AgentRow): Exclude<AgentsSwarmFilter, "all"> {
  if (!hasSubSwarmId(agent)) {
    return "unassigned";
  }
  const raw = rawSwarmHints(agent);
  if (raw.includes("scout")) {
    return "scout";
  }
  if (raw.includes("eval")) {
    return "eval";
  }
  if (raw.includes("sim")) {
    return "sim";
  }
  if (raw.includes("action")) {
    return "action";
  }
  return "unassigned";
}

function agentListLane(agent: AgentRow): AgentHiveLane {
  if (isQueenAgent(agent)) {
    return "queen";
  }
  const b = workerSwarmPillBucket(agent);
  if (b === "unassigned") {
    return "unassigned";
  }
  return b;
}

function roleDisplayName(role: string): string {
  const r = role.toLowerCase();
  const map: Record<string, string> = {
    scraper: "ScraperBee",
    evaluator: "EvaluatorBee",
    simulator: "SimulatorBee",
    reporter: "ReporterBee",
    trader: "TraderBee",
    marketer: "MarketerBee",
    blog_writer: "BlogWriterBee",
    social_poster: "SocialPosterBee",
    learner: "LearnerBee",
    recipe_keeper: "RecipeKeeperBee",
  };
  if (map[r]) {
    return map[r];
  }
  const cleaned = r.replace(/_/g, " ");
  return `${cleaned.charAt(0).toUpperCase()}${cleaned.slice(1)}Bee`;
}

function laneTabLabel(key: Exclude<AgentsSwarmFilter, "all">): string {
  const labels: Record<Exclude<AgentsSwarmFilter, "all">, string> = {
    unassigned: "Unassigned",
    scout: "Scout Swarm",
    eval: "Eval Swarm",
    sim: "Sim Swarm",
    action: "Action Swarm",
  };
  return labels[key];
}

function rosterFilterActiveClass(key: AgentsSwarmFilter): string {
  switch (key) {
    case "all":
      return "qs-pill--active-amber";
    case "unassigned":
      return "qs-pill--active-red";
    case "scout":
      return "qs-pill--active-cyan";
    case "eval":
      return "qs-pill--active-amber";
    case "sim":
      return "qs-pill--active-magenta";
    case "action":
      return "qs-pill--active-green";
    default:
      return "qs-pill--active-amber";
  }
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

interface LaneTheme {
  hexBorder: string;
  barBg: string;
  glow: string;
  listBar: string;
  scoreText: string;
  pillClass: string;
}

function laneTheme(lane: AgentHiveLane, agent: AgentRow): LaneTheme {
  if (lane === "queen") {
    return {
      hexBorder: "border-pollen/90",
      barBg: "bg-pollen",
      glow: "shadow-[0_0_26px_rgb(255_184_0/0.4)]",
      listBar: "bg-pollen",
      scoreText: "text-pollen",
      pillClass: "border-pollen/45 text-pollen",
    };
  }
  if (lane === "unassigned") {
    return {
      hexBorder: "border-pollen/65",
      barBg: "bg-pollen/85",
      glow: "shadow-[0_0_22px_rgb(255_184_0/0.33)]",
      listBar: "bg-pollen/80",
      scoreText: "text-pollen/90",
      pillClass: "border-pollen/35 text-pollen/90",
    };
  }
  const n = agent.name.toLowerCase();
  const orangeAction = lane === "action" && n.includes("action") && (agent.id.charCodeAt(0) ?? 0) % 2 === 1;
  if (lane === "scout") {
    return {
      hexBorder: "border-[#00E5FF]/85",
      barBg: "bg-[#00E5FF]",
      glow: "shadow-[0_0_24px_rgb(0_229_255/0.32)]",
      listBar: "bg-[#00E5FF]",
      scoreText: "text-[#00E5FF]",
      pillClass: "border-[#00E5FF]/45 text-[#00E5FF]",
    };
  }
  if (lane === "eval") {
    return {
      hexBorder: "border-pollen/80",
      barBg: "bg-pollen",
      glow: "shadow-[0_0_24px_rgb(255_184_0/0.28)]",
      listBar: "bg-pollen",
      scoreText: "text-pollen",
      pillClass: "border-pollen/45 text-pollen",
    };
  }
  if (lane === "sim") {
    return {
      hexBorder: "border-alert/80",
      barBg: "bg-alert",
      glow: "shadow-[0_0_24px_rgb(255_0_170/0.28)]",
      listBar: "bg-alert",
      scoreText: "text-alert",
      pillClass: "border-alert/45 text-alert",
    };
  }
  if (orangeAction) {
    return {
      hexBorder: "border-orange-400/85",
      barBg: "bg-orange-400",
      glow: "shadow-[0_0_22px_rgb(251_146_60/0.3)]",
      listBar: "bg-orange-400",
      scoreText: "text-orange-300",
      pillClass: "border-orange-400/50 text-orange-300",
    };
  }
  return {
    hexBorder: "border-success/80",
    barBg: "bg-success",
    glow: "shadow-[0_0_22px_rgb(0_255_136/0.28)]",
    listBar: "bg-success",
    scoreText: "text-success",
    pillClass: "border-success/45 text-success",
  };
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

interface AgentsLiveSectionProps {
  agents: AgentRow[];
  onAgentActivate: (agent: AgentRow) => void;
  onRebalanceHive: () => Promise<void>;
  rebalanceBusy: boolean;
  /** Primary CTA for spawning — dashboard defaults to cockpit anchor. */
  spawnAgentHref?: string;
}

export function AgentsLiveSection({
  agents,
  onAgentActivate,
  onRebalanceHive,
  rebalanceBusy,
  spawnAgentHref,
}: AgentsLiveSectionProps) {
  const [swarmFilter, setSwarmFilter] = useState<AgentsSwarmFilter>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const spawnHref = spawnAgentHref ?? "/#hive-create";

  const counts = useMemo(() => {
    let scout = 0;
    let evalc = 0;
    let sim = 0;
    let action = 0;
    let unassigned = 0;
    for (const a of agents) {
      if (isQueenAgent(a)) {
        continue;
      }
      const L = workerSwarmPillBucket(a);
      if (L === "scout") {
        scout += 1;
      } else if (L === "eval") {
        evalc += 1;
      } else if (L === "sim") {
        sim += 1;
      } else if (L === "action") {
        action += 1;
      } else if (L === "unassigned") {
        unassigned += 1;
      }
    }
    return { all: agents.length, unassigned, scout, eval: evalc, sim, action };
  }, [agents]);

  const roleTypeCount = useMemo(() => new Set(agents.map((a) => a.role.toLowerCase())).size, [agents]);

  const swarmCountDistinct = useMemo(() => {
    const ids = new Set<string>();
    for (const a of agents) {
      if (isQueenAgent(a)) {
        continue;
      }
      if (!hasSubSwarmId(a)) {
        continue;
      }
      ids.add(String(a.sub_swarm_id));
    }
    return ids.size;
  }, [agents]);

  const assignedWorkerCount = useMemo(
    () =>
      agents.filter((a) => !isQueenAgent(a) && workerSwarmPillBucket(a) !== "unassigned").length,
    [agents],
  );

  const filtered = useMemo(() => {
    if (swarmFilter === "all") {
      return agents;
    }
    return agents.filter((a) => !isQueenAgent(a) && workerSwarmPillBucket(a) === swarmFilter);
  }, [agents, swarmFilter]);

  const pills: { key: AgentsSwarmFilter; count: number }[] = [
    { key: "all", count: counts.all },
    { key: "unassigned", count: counts.unassigned },
    { key: "scout", count: counts.scout },
    { key: "eval", count: counts.eval },
    { key: "sim", count: counts.sim },
    { key: "action", count: counts.action },
  ];

  return (
    <section id="hive-live-swarm" className="scroll-mt-24 rounded-3xl border-[3px] border-white/10 bg-[#07070f]/95 p-6 md:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1 md:max-w-[min(100%,48rem)]">
          <h2 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#fafafa] md:text-3xl">Agents</h2>
          <p className="mt-2 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
            {counts.all} bees · {assignedWorkerCount} assigned to swarms · {counts.unassigned} unassigned ·{" "}
            {swarmCountDistinct} swarms with at least one bee · {roleTypeCount} role types
          </p>
          <p className="mt-2 max-w-3xl font-[family-name:var(--font-poppins)] text-xs leading-relaxed text-zinc-600">
            No fixed scout/eval/sim quotas at boot — swarm assignment, management, and displaying learned material will be
            tuned later; filter lanes bind to <span className="text-zinc-500">sub_swarm_id</span> and task type from metadata
            (not automatic assignment from agent name).
          </p>
        </div>
        <div className="flex w-full shrink-0 flex-row flex-wrap items-stretch justify-end gap-3 md:ml-auto md:w-auto md:flex-nowrap md:items-start md:justify-end">
          <Link
            href={spawnHref}
            className="qs-btn qs-btn--ghost inline-flex min-w-[10rem] flex-1 items-center justify-center gap-2 whitespace-nowrap sm:flex-initial"
          >
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            Add agent
          </Link>
          <button
            type="button"
            disabled={rebalanceBusy}
            onClick={() => void onRebalanceHive()}
            className="qs-btn qs-btn--primary inline-flex min-w-[10rem] flex-1 items-center justify-center gap-2 whitespace-nowrap sm:flex-initial disabled:opacity-40"
          >
            <Play className="h-4 w-4 shrink-0" aria-hidden />
            {rebalanceBusy ? "Working…" : "Balance hive"}
          </button>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {pills.map(({ key, count }) => {
            const active = swarmFilter === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSwarmFilter(key)}
                className={cn("qs-pill", active && rosterFilterActiveClass(key))}
              >
                {key === "all"
                  ? `All · ${String(count)}`
                  : `${laneTabLabel(key as Exclude<AgentsSwarmFilter, "all">)} · ${String(count)}`}
              </button>
            );
          })}
        </div>
        <div role="group" aria-label="View" className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={cn("qs-pill gap-1.5", viewMode === "grid" && "qs-pill--active-amber")}
          >
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
            Grid
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={cn("qs-pill gap-1.5", viewMode === "list" && "qs-pill--active-amber")}
          >
            <List className="h-3.5 w-3.5" aria-hidden />
            List
          </button>
        </div>
      </div>

      {viewMode === "grid" ? (
        <div className="qs-hex-grid mx-auto mt-10 max-w-[1200px]">
          {filtered.map((agent) => (
            <HexAgentCard
              key={agent.id}
              agent={agent}
              showPerformance
              onClick={() => onAgentActivate(agent)}
            />
          ))}
        </div>
      ) : (
        <ul className="mt-8 space-y-3">
          {filtered.map((agent) => {
            const lane = agentListLane(agent);
            const theme = laneTheme(lane === "queen" ? "queen" : lane, agent);
            const err = agent.status.toUpperCase() === "ERROR";
            const offline = agent.status.toUpperCase() === "OFFLINE";
            const scoreP = pctScore(agent.performance_score);
            return (
              <li
                key={agent.id}
                className={cn(
                  "flex overflow-hidden rounded-2xl qs-rim bg-black/40",
                  offline && "opacity-[0.78] saturate-[0.42]",
                )}
              >
                <div className={cn("w-1 shrink-0", offline ? "bg-zinc-600/85" : theme.listBar)} aria-hidden />
                <button
                  type="button"
                  onClick={() => onAgentActivate(agent)}
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
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 qs-chip uppercase",
                          theme.pillClass,
                        )}
                      >
                        {lane === "queen" ? "Queen" : laneTabLabel(lane as Exclude<AgentsSwarmFilter, "all">)}
                      </span>
                    </div>
                    <p className="mt-1.5 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">
                      {agentStatusLine(agent)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-2 sm:w-40">
                    <div>
                      <div className="flex items-center justify-between qs-meta-label text-zinc-500">
                        <span>Score</span>
                        <span className={cn(err ? "text-danger" : theme.scoreText)}>
                          {pctScoreDisplay(agent.performance_score)}
                        </span>
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
              </li>
            );
          })}
        </ul>
      )}

      {filtered.length === 0 ? (
        <p className="mt-10 text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
          No agents match this filter.
        </p>
      ) : null}
    </section>
  );
}
