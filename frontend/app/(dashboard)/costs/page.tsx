import Link from "next/link";
import nextDynamic from "next/dynamic";
import { DollarSignIcon, TargetIcon } from "lucide-react";

import { DashboardSectionSkeleton } from "@/components/hive/colony-console-skeleton";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4Card, V4CardHeader, V4PageCanvas, V4Stat } from "@/components/ui/v4";
import { aggregateSpendByModel, consolidateDailySpend } from "@/lib/cost-aggregates";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, OperatorCostSummary, TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

const SpendTrendChart = nextDynamic(
  () => import("@/components/hive/spend-trend-chart").then((mod) => ({ default: mod.SpendTrendChart })),
  { loading: () => <DashboardSectionSkeleton className="h-72" /> },
);

const SystemStatusPanel = nextDynamic(
  () => import("@/components/hive/system-status-panel").then((mod) => ({ default: mod.SystemStatusPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[180px]" /> },
);

const TimeSavedPanel = nextDynamic(
  () => import("@/components/hive/time-saved-panel").then((mod) => ({ default: mod.TimeSavedPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[160px]" /> },
);

function formatUsd(n: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(n);
}

function summarizeWindow(series: OperatorCostSummary["series"], daysRecent: number) {
  const byDay = consolidateDailySpend(series);
  const last = byDay.slice(-daysRecent).reduce((a, r) => a + r.spend_usd, 0);
  const prev = byDay.slice(-daysRecent * 2, -daysRecent).reduce((a, r) => a + r.spend_usd, 0);
  const deltaPct = prev > 0 ? Math.round(((last - prev) / prev) * 100) : 0;
  return { windowSum: last, deltaPct };
}

/** Operator spend cockpit — KPI row, trend curve, providers, pollen-linked top agents. */
export default async function CostsPage() {
  const summary = await hiveServerRawJson<OperatorCostSummary>("/operator/costs/summary?days=35");
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=60");
  const tasks = await hiveServerRawJson<TaskRow[]>("/tasks?limit=200");

  if (!summary) {
    return (
      <V4PageCanvas>
        <HivePageHeader
          title="Costs"
          subtitle="Per LLM · per agent · per swarm · Prometheus CostGovernor"
          actions={
            <Link href="/settings/billing" className="qs-btn qs-btn--ghost qs-btn--sm text-xs uppercase">
              Configure caps
            </Link>
          }
        />
        <p className="rounded-xl border border-alert/30 bg-alert/10 px-4 py-3 text-sm text-(--qs-text-2) lg:hidden">
          Spend ledger syncing — charts appear once the operator API responds.
        </p>
        <p className="text-sm text-(--qs-red)">
          Operator ledger unavailable · try INTERNAL_BACKEND_ORIGIN / proxy JWT.
        </p>
      </V4PageCanvas>
    );
  }

  const byDayFull = consolidateDailySpend(summary.series);
  const todayKey = new Date().toDateString();
  const taskLedgerUsdToday =
    (tasks ?? [])
      .filter((t) => t.created_at && new Date(t.created_at).toDateString() === todayKey)
      .reduce((acc, t) => acc + Number(t.cost_usd ?? 0), 0);

  const providers = aggregateSpendByModel(summary.series).sort((a, b) => b.spend_usd - a.spend_usd);
  const totalWindow = summary.series.reduce((a, row) => a + row.spend_usd, 0);
  const today = summarizeWindow(summary.series, 1);
  const week = summarizeWindow(summary.series, 7);
  const avgDay = week.windowSum > 0 ? week.windowSum / 7 : 0;
  const projectedMonth = avgDay * 30;
  const providerTotal = providers.reduce((a, x) => a + x.spend_usd, 0) || 1;

  const spenders =
    [...(agents ?? [])]
      .sort((a, b) => Number(b.performance_score ?? 0) + b.pollen_points - (Number(a.performance_score ?? 0) + a.pollen_points))
      .slice(0, 6) ?? [];

  const maxPollen = Math.max(...spenders.map((s) => s.pollen_points), 1);

  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Costs"
        subtitle="Per LLM · per agent · per swarm · Prometheus CostGovernor"
        actions={
          <Link href="/settings/billing" className="qs-btn qs-btn--ghost qs-btn--sm text-xs uppercase">
            Configure caps
          </Link>
        }
      />

      <div className="v4-stat-grid">
        <V4Stat
          label="Today"
          value={formatUsd(today.windowSum)}
          icon={DollarSignIcon}
          iconTone="green"
          trend={
            today.deltaPct !== 0
              ? { dir: today.deltaPct > 0 ? "up" : "down", text: `${today.deltaPct > 0 ? "+" : ""}${today.deltaPct}%` }
              : undefined
          }
        />
        <V4Stat
          label="Week (7d)"
          value={formatUsd(week.windowSum)}
          icon={DollarSignIcon}
          iconTone="cyan"
          trend={
            week.deltaPct !== 0
              ? { dir: week.deltaPct > 0 ? "up" : "down", text: `${week.deltaPct > 0 ? "+" : ""}${week.deltaPct}%` }
              : undefined
          }
        />
        <V4Stat
          label={`Window (${summary.window_days}d)`}
          value={formatUsd(totalWindow)}
          icon={DollarSignIcon}
          foot="Rolling LiteLLM burn"
        />
        <V4Stat label="Billing caps" value="Settings" icon={TargetIcon} iconTone="purple" foot="Soft/hard limits per tier" />
      </div>

      <TimeSavedPanel />

      <p className="text-xs text-(--qs-magenta)">
        Task ledger Σ cost_usd (UTC midnight window):{" "}
        <span className="text-(--qs-gold) tabular-nums">{formatUsd(taskLedgerUsdToday)}</span>
      </p>

      <section className="v4-cost-layout">
        <div className="space-y-3 min-w-0">
          <div className="flex flex-wrap justify-between gap-2">
            <h2 className="text-lg text-(--qs-text)">
              Spend trend · {Math.min(summary.window_days, byDayFull.length)}d
            </h2>
            <Link href="/grafana/" className="qs-btn qs-btn--ghost qs-btn--sm text-[10px] uppercase">
              Open Grafana
            </Link>
          </div>
          <SpendTrendChart data={byDayFull.slice(-Math.min(summary.window_days, byDayFull.length))} />
          <div className="flex flex-wrap justify-between gap-2 px-2 text-xs text-(--qs-text-3)">
            <span>Avg ${avgDay.toFixed(2)} / day</span>
            <span>Proj. ${Math.round(projectedMonth)} / month</span>
          </div>
        </div>

        <V4Card className="min-w-0">
          <V4CardHeader title="By LLM provider" />
          <div className="space-y-4">
            {providers.length === 0 ? (
              <p className="text-sm text-(--qs-text-3)">No spend in this window.</p>
            ) : (
              providers.map((p) => {
                const pct = Math.round(((p.spend_usd ?? 0) / providerTotal) * 100);
                return (
                  <div key={p.model}>
                    <div className="flex justify-between text-sm text-(--qs-text)">
                      <span>{p.model}</span>
                      <span>
                        {formatUsd(p.spend_usd)}{" "}
                        <span className="text-[11px] text-(--qs-text-3)">· {pct}%</span>
                      </span>
                    </div>
                    <div className="mt-2 v4-progress-track">
                      <div className="v4-progress-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </V4Card>
      </section>

      <SystemStatusPanel />

      <V4Card>
        <V4CardHeader
          title="Pollen intensity · top bees"
          description="Relative to max in the hive — per-agent LiteLLM cost join still to come."
        />
        <ul className="space-y-5">
          {spenders.map((bee) => {
            const w = Math.max(6, Math.round((bee.pollen_points / maxPollen) * 100));
            return (
              <li key={bee.id}>
                <div className="flex justify-between gap-3 text-sm">
                  <span className="text-(--qs-text)">
                    {bee.name}{" "}
                    <span className="text-[11px] text-(--qs-text-3)">· {bee.role}</span>
                  </span>
                  <span className="text-(--qs-gold) tabular-nums">{Number(bee.pollen_points).toFixed(2)}</span>
                </div>
                <div className="mt-2 v4-progress-track">
                  <div className="v4-progress-fill" style={{ width: `${w}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </V4Card>
    </V4PageCanvas>
  );
}
