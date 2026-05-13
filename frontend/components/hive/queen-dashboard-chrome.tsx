"use client";

import { Suspense, useState } from "react";
import { Activity, Coins, Cpu, ListTodo, Plus, Search, Users, Zap } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { AgentsLiveSection } from "@/components/hive/agents-live-section";
import { SwarmBoardSection } from "@/components/hive/swarm-board-section";
import { TaskQueueSection } from "@/components/hive/task-queue-section";
import { WorkflowsSection } from "@/components/hive/workflows-section";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function formatPollen(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(Math.round(n * 10) / 10);
}

function formatUsd(n: number | null): string {
  if (n === null || Number.isNaN(n)) return "—";
  if (n < 0.01 && n > 0) return `<$0.01`;
  return `$${n.toFixed(2)}`;
}

function statusDotClass(status: string): string {
  const u = status.toUpperCase();
  if (u.includes("RUN")) return "bg-cyan shadow-[0_0_8px_rgb(0_255_255/0.8)]";
  if (u.includes("PEND") || u.includes("QUEUE")) return "bg-pollen shadow-[0_0_8px_rgb(255_184_0/0.45)]";
  if (u.includes("COMP")) return "bg-success";
  if (u === "IDLE") return "bg-success";
  if (u === "PAUSED") return "bg-alert";
  if (u === "OFFLINE" || u === "ERROR" || u.includes("FAIL")) return "bg-danger";
  return "bg-zinc-500";
}

function taskStatusBrief(statusRaw: string): string {
  return statusRaw.replaceAll("_", " ");
}

interface QueenDashboardChromeProps {
  agents: AgentRow[];
  summary: DashboardSummary | null;
  costWindowUsd: number | null;
  filterQuery: string;
  onFilterChange: (q: string) => void;
  onHoneycombAgent: (agent: AgentRow) => void;
  onAgentsReload: () => void | Promise<void>;
  swarmLabelCount: number;
  systemStatus?: SystemStatusPayload | null;
  recentTasks?: TaskRow[];
  telemetryLoading?: boolean;
}

export function QueenDashboardChrome({
  agents,
  summary,
  costWindowUsd,
  filterQuery,
  onFilterChange,
  onHoneycombAgent,
  onAgentsReload,
  swarmLabelCount,
  systemStatus = null,
  recentTasks = [],
  telemetryLoading = false,
}: QueenDashboardChromeProps) {
  const [rebalanceBusy, setRebalanceBusy] = useState(false);
  const pollenTotal = agents.reduce((s, a) => s + (a.pollen_points ?? 0), 0);
  const pendingFallback = summary?.tasks.pending ?? 0;
  const totalAgentsListed = agents.length;
  const totalAgentsGauge = Math.max(totalAgentsListed, systemStatus?.agents_total ?? 0);
  const activeAgents = agents.filter((a) => ["RUNNING", "IDLE", "BUSY"].includes(String(a.status).toUpperCase())).length;

  const runningTasks = systemStatus?.tasks_running ?? 0;
  const queuedTasks = systemStatus?.tasks_pending ?? pendingFallback;
  const llmOk = Boolean(systemStatus?.llm_grok || systemStatus?.llm_anthropic);

  const showKpiPulse = telemetryLoading && !systemStatus;

  const tierBars = (() => {
    const m = summary?.agents.by_hive_tier ?? {};
    const tot = Math.max(1, Object.values(m).reduce((a, b) => a + b, 0));
    const rows = [
      { key: "orchestrator", label: "Queen", bar: "bg-gradient-to-r from-pollen to-amber-600" },
      { key: "manager", label: "Manažéri", bar: "bg-gradient-to-r from-cyan to-teal-500" },
      { key: "worker", label: "Robotníci", bar: "bg-gradient-to-r from-alert to-fuchsia-600" },
      { key: "unknown", label: "Nezaradené", bar: "bg-gradient-to-r from-zinc-500 to-zinc-700" },
    ];
    return rows.map((r) => ({
      ...r,
      pct: Math.round(((m[r.key] ?? 0) / tot) * 100),
      count: m[r.key] ?? 0,
    }));
  })();

  async function rebalanceHive(): Promise<void> {
    setRebalanceBusy(true);
    try {
      const res = await hivePostJson<{ woken?: number; message?: string }>("agents/wake-all", {});
      toast.success(res.message ?? "Pozastavené včely sú späť v idle.");
      await Promise.resolve(onAgentsReload());
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Vyrovnanie zlyhalo";
      toast.error(msg);
    } finally {
      setRebalanceBusy(false);
    }
  }

  return (
    <div className="flex w-full flex-col gap-8">
      {/* Hero + search (desktop feel) */}
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold tracking-tight text-[#fafafa] md:text-4xl">
            Queen Swarm Dashboard
          </h1>
          <p className="mt-2 max-w-2xl font-[family-name:var(--font-inter)] text-sm text-zinc-400">
            {totalAgentsGauge} agentov v sieti · {swarmLabelCount} swarm uzlov · synchronizácia úľa približne každých 5 min
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-3">
          <Link href="/tasks/new" className="qs-btn qs-btn--primary gap-2 px-6 py-3">
            <Plus className="h-4 w-4" aria-hidden />
            Nová úloha
          </Link>
          <Link href="/ballroom" className="qs-btn qs-btn--secondary px-6 py-3">
            Ballroom
          </Link>
        </div>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden />
        <input
          type="search"
          value={filterQuery}
          onChange={(e) => onFilterChange(e.target.value)}
          placeholder="Hľadať agentov, úroveň, meno…"
          className="w-full rounded-2xl border-[2px] border-cyan/20 bg-black/55 py-3.5 pl-11 pr-4 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none ring-pollen/20 placeholder:text-zinc-600 focus:border-pollen/40 focus:ring-2"
          aria-label="Filter agentov"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {showKpiPulse ? (
          <>
            {[0, 1, 2, 3].map((i) => (
              <div key={String(i)} className="animate-pulse rounded-2xl border border-cyan/10 bg-[#0d0d18]/95 p-5">
                <div className="h-7 w-2/5 rounded-lg bg-white/10" />
                <div className="mt-4 h-8 w-1/2 rounded-lg bg-white/10" />
                <div className="mt-3 h-3 w-3/5 rounded bg-white/5" />
              </div>
            ))}
          </>
        ) : (
          <>
            <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
              <div className="flex items-start justify-between gap-2">
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Total agents
                </p>
                <Users className="h-5 w-5 text-cyan/60" aria-hidden />
              </div>
              <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl font-bold text-[#fafafa]">{totalAgentsListed}</p>
              <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-success">Active {activeAgents}</p>
            </article>
            <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
              <div className="flex items-start justify-between gap-2">
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Running tasks
                </p>
                <Zap className="h-5 w-5 text-data/80" aria-hidden />
              </div>
              <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl font-bold text-data">{runningTasks}</p>
              <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">From system pulse</p>
            </article>
            <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
              <div className="flex items-start justify-between gap-2">
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Queued tasks
                </p>
                <ListTodo className="h-5 w-5 text-pollen/70" aria-hidden />
              </div>
              <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl font-bold text-pollen">{queuedTasks}</p>
              <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">Pending lane</p>
            </article>
            <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
              <div className="flex items-start justify-between gap-2">
                <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  LLM status
                </p>
                <Cpu className="h-5 w-5 text-pollen/70" aria-hidden />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span
                  className={cn(
                    "h-3 w-3 rounded-full",
                    llmOk ? "bg-success shadow-[0_0_10px_rgb(0_255_136/0.8)]" : "bg-danger shadow-[0_0_10px_rgb(255_51_102/0.55)]",
                  )}
                  aria-hidden
                />
                <p className="font-[family-name:var(--font-poppins)] text-lg font-bold text-[#fafafa]">
                  {llmOk ? "Routed" : "Degraded"}
                </p>
              </div>
              <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                Grok {systemStatus?.llm_grok ? "✓" : "—"} · Claude {systemStatus?.llm_anthropic ? "✓" : "—"}
              </p>
            </article>
          </>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border-[2px] border-white/[0.06] bg-[#0a0a12]/90 p-5 sm:col-span-2 xl:col-span-2">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Pollen (roster)
            </p>
            <Activity className="h-5 w-5 text-success/80" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl font-bold text-pollen">{formatPollen(pollenTotal)}</p>
        </article>
        <article className="rounded-2xl border-[2px] border-white/[0.06] bg-[#0a0a12]/90 p-5 sm:col-span-2 xl:col-span-2">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Náklady (30 dní)
            </p>
            <Coins className="h-5 w-5 text-pollen/70" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl font-bold text-[#fafafa]">{formatUsd(costWindowUsd)}</p>
        </article>
      </div>

      {agents.length === 0 ? (
        <div className="rounded-2xl border border-pollen/30 bg-black/35 px-5 py-4 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-300">
          No agents in the hive yet —{" "}
          <Link href="/agents/new" className="font-semibold text-pollen underline-offset-4 hover:underline">
            Spawn first agent
          </Link>
        </div>
      ) : null}

      <AgentsLiveSection
        agents={agents}
        onAgentActivate={onHoneycombAgent}
        onRebalanceHive={rebalanceHive}
        rebalanceBusy={rebalanceBusy}
      />

      <SwarmBoardSection />

      <Suspense
        fallback={
          <div
            id="hive-workflows"
            className="scroll-mt-24 h-44 animate-pulse rounded-3xl bg-white/[0.04]"
          />
        }
      >
        <WorkflowsSection />
      </Suspense>

      <TaskQueueSection />

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl border-[2px] border-cyan/15 bg-[#0a0a14]/90 p-6">
          <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Výkon podľa tieru</h3>
          <p className="mt-1 text-xs text-zinc-500">Podiel agentov v úli (z API summary)</p>
          <ul className="mt-5 space-y-4">
            {tierBars.map((row) => (
              <li key={row.key}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-zinc-300">{row.label}</span>
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-cyan/70">{row.pct}% · {row.count}</span>
                </div>
                <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-black/60">
                  <div
                    className={cn("h-full rounded-full transition-all", row.bar)}
                    style={{ width: `${row.pct}%`, boxShadow: "0 0 12px rgb(0 255 255 / 0.2)" }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-3xl border-[2px] border-cyan/15 bg-[#0a0a14]/90 p-6">
          <h3 className="font-[family-name:var(--font-poppins)] text-lg font-semibold text-[#fafafa]">Recent tasks</h3>
          <p className="mt-1 text-xs text-zinc-500">Latest {Math.min(8, recentTasks.length)} rows from /api/v1/tasks</p>
          <ul className="mt-5 divide-y divide-cyan/10">
            {recentTasks.length === 0 ? (
              <li className="py-6 text-center text-sm text-zinc-600">No tasks synced yet.</li>
            ) : (
              recentTasks.slice(0, 8).map((t) => (
                <li key={t.id} className="flex gap-3 py-3">
                  <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", statusDotClass(t.status))} aria-hidden />
                  <div className="min-w-0 flex-1">
                    <Link href="/tasks" className="truncate font-[family-name:var(--font-inter)] text-sm text-[#fafafa] hover:text-pollen">
                      {t.title}
                    </Link>
                    <p className="mt-0.5 truncate font-[family-name:var(--font-jetbrains-mono)] text-[11px] uppercase text-zinc-500">{taskStatusBrief(t.status)}</p>
                  </div>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>
    </div>
  );
}
