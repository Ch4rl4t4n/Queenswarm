"use client";

import Link from "next/link";
import { Hexagon, LayoutGrid, List, Play, Plus } from "lucide-react";
import { useMemo, useState } from "react";

import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** Tab filter for the live roster (no ``queen`` lane — Queen rides only under ``all``). */
export type AgentsSwarmFilter = "all" | "unassigned" | "scout" | "eval" | "sim" | "action";

/** Placement derived from DB (``swarm_id`` + hydrated ``swarm_purpose``), plus ``queen`` tier. */
export type AgentHiveLane = "queen" | "unassigned" | "scout" | "eval" | "sim" | "action";

type ViewMode = "grid" | "list";

function isQueenAgent(agent: AgentRow): boolean {
  const tier = (agent.hive_tier ?? "").toLowerCase();
  return tier === "orchestrator" || agent.name.toLowerCase() === "orchestrator";
}

/** Map API ``SwarmPurpose`` (and legacy name hints) to dashboard lanes. */
function purposeToLane(purpose: string | null | undefined): "scout" | "eval" | "sim" | "action" | null {
  const u = (purpose ?? "").toLowerCase();
  if (u === "scout") {
    return "scout";
  }
  if (u === "eval") {
    return "eval";
  }
  if (u === "simulation") {
    return "sim";
  }
  if (u === "action") {
    return "action";
  }
  return null;
}

function agentLane(agent: AgentRow): AgentHiveLane {
  if (isQueenAgent(agent)) {
    return "queen";
  }
  const sid = agent.swarm_id;
  const anchored = sid !== undefined && sid !== null && String(sid).trim().length > 0;
  if (!anchored) {
    return "unassigned";
  }
  const lane = purposeToLane(agent.swarm_purpose);
  if (lane) {
    return lane;
  }
  const label = (agent.swarm_name ?? "").toLowerCase();
  if (label.includes("scout")) {
    return "scout";
  }
  if (label.includes("eval")) {
    return "eval";
  }
  if (label.includes("sim")) {
    return "sim";
  }
  if (label.includes("action")) {
    return "action";
  }
  /** FK without join metadata — safest neutral bucket until enrichment lands. */
  return "unassigned";
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
    unassigned: "Nezaradení",
    scout: "Scout Swarm",
    eval: "Eval Swarm",
    sim: "Sim Swarm",
    action: "Action Swarm",
  };
  return labels[key];
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
      hexBorder: "border-zinc-400/70",
      barBg: "bg-zinc-400",
      glow: "shadow-[0_0_18px_rgb(161_161_170/0.28)]",
      listBar: "bg-zinc-500",
      scoreText: "text-zinc-300",
      pillClass: "border-zinc-500/50 text-zinc-400",
    };
  }
  const n = agent.name.toLowerCase();
  const orangeAction = lane === "action" && n.includes("action") && (agent.id.charCodeAt(0) ?? 0) % 2 === 1;
  if (lane === "scout") {
    return {
      hexBorder: "border-cyan/85",
      barBg: "bg-cyan",
      glow: "shadow-[0_0_24px_rgb(0_255_255/0.32)]",
      listBar: "bg-cyan",
      scoreText: "text-cyan",
      pillClass: "border-cyan/45 text-cyan",
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
    return "bg-zinc-500";
  }
  if (u === "PAUSED") {
    return "bg-alert";
  }
  if (u === "OFFLINE" || u === "ERROR") {
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
    return "Spracúvam úlohu…";
  }
  if (u === "ERROR") {
    return "Chyba — vyžaduje pozornosť";
  }
  if (u === "PAUSED") {
    return "Pozastavené";
  }
  return "Čakám na handoff";
}

interface AgentsLiveSectionProps {
  agents: AgentRow[];
  onAgentActivate: (agent: AgentRow) => void;
  onRebalanceHive: () => Promise<void>;
  rebalanceBusy: boolean;
}

export function AgentsLiveSection({
  agents,
  onAgentActivate,
  onRebalanceHive,
  rebalanceBusy,
}: AgentsLiveSectionProps) {
  const [swarmFilter, setSwarmFilter] = useState<AgentsSwarmFilter>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

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
      const L = agentLane(a);
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

  const swarmCountDistinct = useMemo(
    () => new Set(agents.map((a) => a.swarm_id).filter(Boolean)).size,
    [agents],
  );

  const assignedWorkerCount = useMemo(
    () => agents.filter((a) => !isQueenAgent(a) && Boolean(a.swarm_id)).length,
    [agents],
  );

  const filtered = useMemo(() => {
    if (swarmFilter === "all") {
      return agents;
    }
    return agents.filter((a) => agentLane(a) === swarmFilter);
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
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-bold text-[#fafafa] md:text-3xl">Agenti</h2>
          <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
            {counts.all} včiel · {assignedWorkerCount} zaradených do swarmov · {counts.unassigned} nezaradených ·{" "}
            {swarmCountDistinct} swarmov s aspoň jednou včelou · {roleTypeCount} typov rolí
          </p>
          <p className="mt-2 max-w-3xl font-[family-name:var(--font-inter)] text-xs leading-relaxed text-zinc-600">
            Žiadne pevné kvóty scout/eval/sim pri štarte — priradenie swarmu, manažment a zobrazenie naučeného obsahu sa
            doladia neskôr; zoznam používa výhradne <span className="text-zinc-500">swarm_id</span> zo servera (nie hádanie podľa mena).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/#hive-create"
            className="inline-flex items-center gap-2 rounded-2xl border border-white/20 bg-black/50 px-4 py-2.5 font-[family-name:var(--font-inter)] text-sm font-semibold text-[#fafafa] transition hover:border-cyan/35 hover:text-pollen"
          >
            <Plus className="h-4 w-4" aria-hidden />
            Pridať agenta
          </Link>
          <button
            type="button"
            disabled={rebalanceBusy}
            onClick={() => void onRebalanceHive()}
            className="inline-flex items-center gap-2 rounded-2xl border-[2px] border-pollen bg-pollen px-4 py-2.5 font-[family-name:var(--font-space-grotesk)] text-sm font-bold text-black shadow-[0_0_28px_rgb(255_184_0/0.42)] transition hover:bg-[#ffc933] disabled:opacity-45"
          >
            <Play className="h-4 w-4" aria-hidden />
            {rebalanceBusy ? "Prebieha…" : "Vyrovnať úľ"}
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
                className={cn(
                  "rounded-full border px-3 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold transition",
                  active
                    ? "border-pollen/70 bg-pollen/10 text-pollen shadow-[0_0_18px_rgb(255_184_0/0.22)]"
                    : "border-white/10 bg-black/40 text-zinc-500 hover:border-cyan/25 hover:text-zinc-300",
                )}
              >
                {key === "all"
                  ? `Všetko · ${String(count)}`
                  : `${laneTabLabel(key as Exclude<AgentsSwarmFilter, "all">)} · ${String(count)}`}
              </button>
            );
          })}
        </div>
        <div
          role="group"
          aria-label="Zobrazenie"
          className="flex rounded-xl border border-white/10 bg-black/45 p-1"
        >
          <button
            type="button"
            onClick={() => setViewMode("grid")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold transition",
              viewMode === "grid" ? "bg-white/10 text-pollen" : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
            Mriežka
          </button>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold transition",
              viewMode === "list" ? "bg-white/10 text-pollen" : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            <List className="h-3.5 w-3.5" aria-hidden />
            Zoznam
          </button>
        </div>
      </div>

      {viewMode === "grid" ? (
        <ul className="mx-auto mt-10 grid max-w-[1200px] grid-cols-2 justify-items-center gap-x-3 gap-y-10 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {filtered.map((agent, i) => {
            const lane = agentLane(agent);
            const theme = laneTheme(lane === "queen" ? "queen" : lane, agent);
            const idle = agent.status.toUpperCase() === "IDLE";
            const err = agent.status.toUpperCase() === "ERROR";
            const scoreP = pctScore(agent.performance_score);
            return (
              <li
                key={agent.id}
                className={cn("flex justify-center", i % 2 === 1 && "sm:mt-6 md:mt-10", i % 2 === 0 && "md:mt-2")}
              >
                <div
                  className={cn(
                    "hive-hex-clip-flat hive-hex-flat-tile",
                    "flex flex-col justify-center border-[9px] bg-[#0a0a12]/95 px-2.5 py-2 transition hover:brightness-110",
                    theme.hexBorder,
                    theme.glow,
                    idle && "opacity-75 brightness-[0.92]",
                  )}
                >
                  <button
                    type="button"
                    className="flex w-full flex-col items-center text-center outline-none focus-visible:ring-2 focus-visible:ring-pollen/50"
                    onClick={() => onAgentActivate(agent)}
                  >
                    <span className={cn("mb-2 h-2 w-2 rounded-full", statusDotClass(agent.status))} aria-hidden />
                    <p className="w-full truncate font-[family-name:var(--font-space-grotesk)] text-sm font-bold text-[#fafafa]">
                      {agent.name}
                    </p>
                    <p className="mt-0.5 w-full truncate font-[family-name:var(--font-inter)] text-[10px] text-zinc-500">
                      {roleDisplayName(agent.role)}
                    </p>
                    <p className="mt-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-300">
                      Pollen {formatPollen(agent.pollen_points ?? 0)}
                    </p>
                    <p
                      className={cn(
                        "font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold",
                        err ? "text-danger" : theme.scoreText,
                      )}
                    >
                      Skóre {pctScoreDisplay(agent.performance_score)}
                    </p>
                    {scoreP > 0 && !err ? (
                      <div className="mt-1 h-1 w-full max-w-[5.5rem] overflow-hidden rounded-full bg-black/60">
                        <div className={cn("h-full rounded-full", theme.barBg)} style={{ width: `${scoreP}%` }} />
                      </div>
                    ) : null}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <ul className="mt-8 space-y-3">
          {filtered.map((agent) => {
            const lane = agentLane(agent);
            const theme = laneTheme(lane === "queen" ? "queen" : lane, agent);
            const err = agent.status.toUpperCase() === "ERROR";
            const scoreP = pctScore(agent.performance_score);
            return (
              <li
                key={agent.id}
                className="flex overflow-hidden rounded-2xl border border-white/[0.07] bg-black/40"
              >
                <div className={cn("w-1 shrink-0", theme.listBar)} aria-hidden />
                <button
                  type="button"
                  onClick={() => onAgentActivate(agent)}
                  className="flex min-w-0 flex-1 flex-col gap-3 px-4 py-3 text-left transition hover:bg-white/[0.03] sm:flex-row sm:items-center sm:gap-6"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn("h-2 w-2 shrink-0 rounded-full", statusDotClass(agent.status))} aria-hidden />
                      <span className="font-[family-name:var(--font-space-grotesk)] text-sm font-bold text-[#fafafa]">
                        {agent.name}
                      </span>
                      <span className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                        {roleDisplayName(agent.role)}
                      </span>
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase",
                          theme.pillClass,
                        )}
                      >
                        {lane === "queen" ? "Queen" : laneTabLabel(lane as Exclude<AgentsSwarmFilter, "all">)}
                      </span>
                    </div>
                    <p className="mt-1.5 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                      {agentStatusLine(agent)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-2 sm:w-40">
                    <div>
                      <div className="flex items-center justify-between text-[10px] font-[family-name:var(--font-jetbrains-mono)] uppercase tracking-wide text-zinc-500">
                        <span>Skóre</span>
                        <span className={cn(err ? "text-danger" : theme.scoreText)}>
                          {pctScoreDisplay(agent.performance_score)}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-black/60">
                        <div className={cn("h-full rounded-full", theme.barBg)} style={{ width: `${scoreP}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 font-[family-name:var(--font-jetbrains-mono)] text-xs text-pollen">
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
        <p className="mt-10 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-500">
          Žiadni agenti v tomto filtri.
        </p>
      ) : null}
    </section>
  );
}
