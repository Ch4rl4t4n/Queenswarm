"use client";

import { Suspense, useState } from "react";
import { Activity, Coins, ListTodo, Plus, Search, Users } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { AgentsLiveSection } from "@/components/hive/agents-live-section";
import { SwarmBoardSection } from "@/components/hive/swarm-board-section";
import { TaskQueueSection } from "@/components/hive/task-queue-section";
import { WorkflowsSection } from "@/components/hive/workflows-section";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { AgentRow, DashboardSummary } from "@/lib/hive-types";
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
  if (u === "RUNNING") return "bg-cyan shadow-[0_0_8px_rgb(0_255_255/0.8)]";
  if (u === "IDLE") return "bg-success";
  if (u === "PAUSED") return "bg-alert";
  if (u === "OFFLINE" || u === "ERROR") return "bg-danger";
  return "bg-zinc-500";
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
}: QueenDashboardChromeProps) {
  const [rebalanceBusy, setRebalanceBusy] = useState(false);
  const pollenTotal = agents.reduce((s, a) => s + (a.pollen_points ?? 0), 0);
  const pending = summary?.tasks.pending ?? 0;
  const totalAgents = summary?.agents.total ?? agents.length;
  const running = agents.filter((a) => a.status?.toUpperCase() === "RUNNING").length;

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

  const recent = [...agents]
    .filter((a) => (a.current_task_title ?? "").trim().length > 0)
    .slice(0, 6);

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
          <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-bold tracking-tight text-[#fafafa] md:text-4xl">
            Queen Swarm Dashboard
          </h1>
          <p className="mt-2 max-w-2xl font-[family-name:var(--font-inter)] text-sm text-zinc-400">
            {totalAgents} agentov v sieti · {swarmLabelCount} swarm uzlov · synchronizácia úľa približne každých 5 min
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-3">
          <Link
            href="/#hive-task"
            className={cn(
              "inline-flex items-center gap-2 rounded-2xl border-[3px] border-pollen bg-pollen px-5 py-3 font-[family-name:var(--font-space-grotesk)] text-sm font-bold text-black shadow-[0_0_28px_rgb(255_184_0/0.45)] transition hover:bg-[#ffc933]",
            )}
          >
            <Plus className="h-4 w-4" aria-hidden />
            Nová úloha
          </Link>
          <Link
            href="/ballroom"
            className="inline-flex items-center gap-2 rounded-2xl border-[2px] border-cyan/35 bg-black/50 px-4 py-3 text-sm font-semibold text-cyan hover:border-pollen/40 hover:text-pollen"
          >
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
        <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Agenti celkom
            </p>
            <Users className="h-5 w-5 text-cyan/60" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold text-[#fafafa]">{totalAgents}</p>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-success">{running > 0 ? `${String(running)} beh` : "Stabilné"}</p>
        </article>
        <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Úlohy v rade
            </p>
            <ListTodo className="h-5 w-5 text-pollen/70" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold text-[#fafafa]">{pending}</p>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">Pending backlog</p>
        </article>
        <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Pollen
            </p>
            <Activity className="h-5 w-5 text-success/80" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold text-pollen">{formatPollen(pollenTotal)}</p>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">Súčet z registra</p>
        </article>
        <article className="rounded-2xl border-[2px] border-cyan/20 bg-[#0d0d18]/95 p-5 shadow-[inset_0_0_0_1px_rgb(0_255_255/0.06)]">
          <div className="flex items-start justify-between gap-2">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Náklady (30 dní)
            </p>
            <Coins className="h-5 w-5 text-pollen/70" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-space-grotesk)] text-3xl font-bold text-[#fafafa]">{formatUsd(costWindowUsd)}</p>
          <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">LLM ledger</p>
        </article>
      </div>

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
          <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Výkon podľa tieru</h3>
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
          <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">Nedávna aktivita</h3>
          <p className="mt-1 text-xs text-zinc-500">Úlohy naviazané na agentov</p>
          <ul className="mt-5 divide-y divide-cyan/10">
            {recent.length === 0 ? (
              <li className="py-6 text-center text-sm text-zinc-600">Zatiaľ bez otvorených úloh v dashboarde.</li>
            ) : (
              recent.map((a) => (
                <li key={a.id} className="flex gap-3 py-3">
                  <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", statusDotClass(a.status))} aria-hidden />
                  <div className="min-w-0">
                    <p className="truncate font-[family-name:var(--font-inter)] text-sm text-[#fafafa]">{a.current_task_title}</p>
                    <p className="mt-0.5 truncate font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">{a.name}</p>
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
