import Link from "next/link";

import { SpendTrendChart } from "@/components/hive/spend-trend-chart";
import { DashboardBeeHexGrid } from "@/components/hive/dashboard-bee-hex-grid";
import { DanceStrip } from "@/components/hive/dance-strip";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { LiveSwarmToolbar } from "@/components/hive/live-swarm-toolbar";
import { NeonButton } from "@/components/ui/neon-button";
import { consolidateDailySpend } from "@/lib/cost-aggregates";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, DashboardSummary, OperatorCostSummary, TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

function formatUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);
}

function onlineAgents(byStatus: Record<string, number>): { online: number; total: number } {
  let total = 0;
  for (const v of Object.values(byStatus)) {
    total += v;
  }
  let down = 0;
  for (const [k, v] of Object.entries(byStatus)) {
    const u = k.toUpperCase();
    if (u === "OFFLINE" || u === "ERROR") {
      down += v;
    }
  }
  return { online: Math.max(0, total - down), total };
}

function purposeBarAccent(purposeKey: string): string {
  const p = purposeKey.toLowerCase().replaceAll("_", " ");
  if (p.includes("scout")) return "shadow-[0_0_14px_rgb(0_255_255/0.42)] bg-data";
  if (p.includes("eval")) return "shadow-[0_0_14px_rgb(255_184_0/0.45)] bg-pollen";
  if (p.includes("sim")) return "shadow-[0_0_14px_rgb(255_0_170/0.45)] bg-alert";
  if (p.includes("action")) return "shadow-[0_0_14px_rgb(0_255_136/0.45)] bg-success";
  return "bg-zinc-500";
}

function formatPurposeLabel(purposeKey: string): string {
  return purposeKey.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default async function HiveHomeDashboard() {
  const summary = await hiveServerRawJson<DashboardSummary>("/dashboard/summary");
  const costs = await hiveServerRawJson<OperatorCostSummary>("/operator/costs/summary?days=25");

  if (!summary) {
    return (
      <div className="rounded-3xl border border-alert/35 bg-black/60 p-8 text-alert">
        <p className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-pollen">
          Dashboard data unavailable
        </p>
        <p className="mt-4 max-w-xl font-[family-name:var(--font-inter)] text-sm leading-relaxed text-zinc-400">
          Server render could not reach the hive API via the session cookie loopback proxy.
          Confirm you are logged in, then reload. Operators may also verify{" "}
          <code className="font-mono text-xs text-data">FRONTEND_INTERNAL_ORIGIN</code>,{" "}
          <code className="font-mono text-xs text-data">INTERNAL_BACKEND_ORIGIN</code>, and JWT cookies.
        </p>
      </div>
    );
  }

  const trendSeries = costs ? consolidateDailySpend(costs.series).slice(-14) : [];
  const { total } = onlineAgents(summary.agents.by_status);
  const purposePairs = Object.entries(summary.swarms.by_purpose);
  const swarmDenom = purposePairs.reduce((acc, [, val]) => acc + Number(val), 0) || 1;
  const topPurposes = purposePairs.slice(0, 4);

  const agentsLedger = (await hiveServerRawJson<AgentRow[]>("/agents?limit=400")) ?? [];
  const tasksLedger = (await hiveServerRawJson<TaskRow[]>("/tasks?limit=500")) ?? [];

  const activeAgents = agentsLedger.filter((a) => !["offline", "error"].includes(a.status.toLowerCase())).length;
  const tasksToday = tasksLedger.filter((t) => {
    if (!t.created_at) return false;
    return new Date(t.created_at).toDateString() === new Date().toDateString();
  }).length;
  const todayKey = new Date().toDateString();
  const simsPassed = tasksLedger.filter((t) => {
    const st = (t.status ?? "").toLowerCase();
    if (st !== "completed") return false;
    let c = t.confidence_score;
    const r = t.result;
    if ((c === null || c === undefined || Number.isNaN(c)) && r && typeof r === "object" && "confidence_pct" in r) {
      const pct = Number((r as { confidence_pct?: unknown }).confidence_pct);
      c = Number.isNaN(pct) ? undefined : pct / 100;
    }
    const score = typeof c === "number" && !Number.isNaN(c) ? Math.max(0, Math.min(1, c)) : 0;
    return score >= 0.8;
  }).length;
  const costToday = tasksLedger
    .filter((t) => t.created_at && new Date(t.created_at).toDateString() === todayKey)
    .reduce((sum, t) => sum + Number(t.cost_usd ?? 0), 0);

  const liveStats = [
    {
      label: "Active Bees",
      value: `${activeAgents} / ${agentsLedger.length}`,
      icon: "🐝",
      color: "#00FF88",
      glow: "0 0 20px rgb(0 255 136 / 0.27)",
    },
    {
      label: "Tasks Today",
      value: tasksToday,
      icon: "⚡",
      color: "#FFB800",
      glow: "0 0 20px rgb(255 184 0 / 0.27)",
    },
    {
      label: "High Confidence",
      value: simsPassed,
      icon: "✅",
      color: "#00FFFF",
      glow: "0 0 20px rgb(0 255 255 / 0.27)",
    },
    {
      label: "Cost Today",
      value: formatUsd(costToday),
      icon: "💰",
      color: "#FF00AA",
      glow: "0 0 20px rgb(255 0 170 / 0.27)",
    },
  ];
  return (
    <div className="space-y-10 pb-14">
      <HivePageHeader
        title="Queen Swarm Dashboard"
        subtitle={`100+ autonomous agents running 24/7 across ${summary.swarms.total} specialized swarm${summary.swarms.total === 1 ? "" : "s"} · pollen window ${summary.pollen.window_hours}h.`}
        actions={
          <NeonButton
            variant="primary"
            asChild
            className="border-pollen bg-pollen px-5 py-3 font-[family-name:var(--font-space-grotesk)] text-black shadow-[0_0_34px_rgb(255_184_0/0.52)] hover:bg-[#ffc933]"
          >
            <Link href="/tasks">+ New task</Link>
          </NeonButton>
        }
      />

      <section className="grid grid-cols-2 gap-3 lg:gap-4 xl:grid-cols-4">
        {liveStats.map((stat) => (
          <div
            key={stat.label}
            className="flex flex-col gap-2 rounded-xl border border-cyan/[0.12] bg-[#0d0d2b] p-5"
            style={{ boxShadow: stat.glow }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-500">{stat.label}</span>
              <span className="text-xl">{stat.icon}</span>
            </div>
            <div
              className="text-3xl font-bold tabular-nums font-[family-name:var(--font-space-grotesk)]"
              style={{ color: stat.color }}
            >
              {stat.value}
            </div>
          </div>
        ))}
      </section>

      <DashboardBeeHexGrid rosterTarget={total} />

      <section className="relative overflow-hidden rounded-[22px] border border-white/[0.09] bg-gradient-to-br from-[#14141c] via-[#0f0f14] to-[#0a0a0f] p-6 shadow-[0_32px_80px_rgba(0,0,0,0.55)] lg:p-8">
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[0.45] hive-bg-pattern" />
        <div className="relative flex flex-col gap-6">
          <div className="flex flex-col gap-4 border-b border-white/[0.06] pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold tracking-tight text-[#fafafa]">
                Live agent swarm
              </h2>
              <p className="mt-2 max-w-xl font-[family-name:var(--font-inter)] text-sm text-zinc-500">
                Spend telemetry + operator tools · bee lattice above refreshes every five seconds.
              </p>
            </div>
            <LiveSwarmToolbar />
          </div>

          <div className="min-w-0 space-y-6">
            {trendSeries.length > 1 ? (
              <div>
                <p className="font-[family-name:var(--font-space-grotesk)] text-sm font-semibold text-[#fafafa]">
                  Spend pulse
                </p>
                <p className="mt-1 font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                  Consolidated ledger · last ~{costs?.window_days ?? "—"} days
                </p>
                <div className="mt-3">
                  <SpendTrendChart data={trendSeries} />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-[20px] border border-white/[0.08] bg-[#13131a]/96 p-6 shadow-[inset_0_0_0_1px_rgb(255_184_0/0.05)]">
          <header className="mb-5">
            <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
              Swarm mix
            </h2>
            <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
              Purpose-weighted vitality across decentralized roves
            </p>
          </header>
          <div className="space-y-5">
            {topPurposes.map(([purpose, raw]) => {
              const pct = Math.min(100, Math.round((Number(raw) / swarmDenom) * 100));
              return (
                <div key={purpose}>
                  <div className="flex justify-between gap-2 font-[family-name:var(--font-inter)] text-sm text-zinc-400">
                    <span>{formatPurposeLabel(purpose)}</span>
                    <span className="tabular-nums text-[#fafafa]">{pct}%</span>
                  </div>
                  <div className="mt-2 h-3 overflow-hidden rounded-full bg-black/60">
                    <div
                      className={`h-full rounded-full opacity-95 ${purposeBarAccent(purpose)}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <DanceStrip dances={summary.waggle_dances} />
      </section>

      <footer className="border-t border-white/[0.06] pt-6 text-center font-[family-name:var(--font-inter)] text-xs text-zinc-500">
        QueenSwarm · verified simulations ·{" "}
        <Link href="/leaderboard" className="text-pollen hover:underline">
          leaderboard
        </Link>{" "}
        · global sync · rapid loop
      </footer>
    </div>
  );
}
