import Link from "next/link";
import { DollarSignIcon, TargetIcon } from "lucide-react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SpendTrendChart } from "@/components/hive/spend-trend-chart";
import { SystemStatusPanel } from "@/components/hive/system-status-panel";
import { NeonButton } from "@/components/ui/neon-button";
import { aggregateSpendByModel, consolidateDailySpend } from "@/lib/cost-aggregates";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, OperatorCostSummary, TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

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

function barColor(idx: number): string {
  return ["bg-success", "bg-orange-400", "bg-data"][idx % 3];
}

/** Operator spend cockpit — KPI row, trend curve, providers, pollen-linked top agents. */
export default async function CostsPage() {
  const summary = await hiveServerRawJson<OperatorCostSummary>("/operator/costs/summary?days=35");
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=60");
  const tasks = await hiveServerRawJson<TaskRow[]>("/tasks?limit=800");

  if (!summary) {
    return (
      <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">
        Operator ledger nedostupný · skús INTERNAL_BACKEND_ORIGIN / proxy JWT.
      </p>
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
  const capUsd = 500;

  const spenders =
    [...(agents ?? [])]
      .sort((a, b) => Number(b.performance_score ?? 0) + b.pollen_points - (Number(a.performance_score ?? 0) + a.pollen_points))
      .slice(0, 6) ?? [];

  const maxPollen = Math.max(...spenders.map((s) => s.pollen_points), 1);

  return (
    <div className="space-y-10">
      <HivePageHeader
        title="Costs"
        subtitle="Per LLM · per agent · per swarm · Prometheus CostGovernor"
        actions={
          <NeonButton type="button" variant="ghost" className="text-xs uppercase">
            Configure caps
          </NeonButton>
        }
      />

      <section className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiChip label="Today" value={formatUsd(today.windowSum)} delta={today.deltaPct} />
        <KpiChip label="Week (7d)" value={formatUsd(week.windowSum)} delta={week.deltaPct} />
        <KpiChip label={`Window (${summary.window_days}d)`} value={formatUsd(totalWindow)} sub="Rolling LiteLLM burn" />
        <aside className="rounded-2xl border border-alert/25 bg-hive-card/90 p-5 shadow-[inset_0_0_0_1px_rgb(255_0_170/0.12)]">
          <div className="flex justify-between gap-2">
            <p className="font-[family-name:var(--font-inter)] text-xs uppercase tracking-[0.14em] text-muted-foreground">Cap</p>
            <TargetIcon className="h-5 w-5 text-alert" aria-hidden />
          </div>
          <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl text-pollen">{formatUsd(capUsd)}</p>
          <p className="mt-2 font-[family-name:var(--font-inter)] text-xs text-muted-foreground">Auto-pause at 100%</p>
        </aside>
      </section>

      <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-alert">
        Task ledger Σ cost_usd (UTC midnight window):{" "}
        <span className="text-pollen tabular-nums">{formatUsd(taskLedgerUsdToday)}</span>
      </p>

      <section className="grid gap-6 xl:grid-cols-5">
        <div className="space-y-3 xl:col-span-3">
          <div className="flex flex-wrap justify-between gap-2">
            <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">
              Spend trend · {Math.min(summary.window_days, byDayFull.length)}d
            </h2>
            <NeonButton asChild variant="ghost" className="text-[10px] uppercase">
              <Link href="/grafana/">Open Grafana</Link>
            </NeonButton>
          </div>
          <SpendTrendChart data={byDayFull.slice(-Math.min(summary.window_days, byDayFull.length))} />
          <div className="flex flex-wrap justify-between gap-2 px-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">
            <span>Avg ${avgDay.toFixed(2)} / day</span>
            <span>Proj. ${Math.round(projectedMonth)} / month</span>
          </div>
        </div>

        <div className="space-y-3 xl:col-span-2">
          <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">By LLM provider</h2>
          <div className="space-y-4 rounded-2xl border border-cyan/[0.1] bg-hive-card/90 p-5">
            {providers.length === 0 ? (
              <p className="font-[family-name:var(--font-inter)] text-sm text-zinc-500">Žiadny spend v tomto okne.</p>
            ) : (
              providers.map((p, idx) => {
                const pct = Math.round(((p.spend_usd ?? 0) / (providers.reduce((a, x) => a + x.spend_usd, 0) || 1)) * 100);
                return (
                  <div key={p.model}>
                    <div className="flex justify-between font-[family-name:var(--font-inter)] text-sm text-[#fafafa]">
                      <span>{p.model}</span>
                      <span>
                        {formatUsd(p.spend_usd)}{" "}
                        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">· {pct}%</span>
                      </span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/50">
                      <div className={cn("h-full rounded-full", barColor(idx))} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </section>

      <SystemStatusPanel />

      <section className="rounded-3xl border border-cyan/[0.1] bg-hive-card/90 p-6">
        <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">Pollen intensity · top bees</h2>
        <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
          Relatívne oproti max v rožku — per-agent LiteLLM cost join ešte pribudne.
        </p>
        <ul className="mt-8 space-y-5">
          {spenders.map((bee, idx) => {
            const w = Math.max(6, Math.round((bee.pollen_points / maxPollen) * 100));
            return (
              <li key={bee.id}>
                <div className="flex justify-between gap-3 font-[family-name:var(--font-inter)] text-sm">
                  <span className="text-[#fafafa]">
                    {bee.name}{" "}
                    <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">· {bee.role}</span>
                  </span>
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-pollen tabular-nums">
                    {Number(bee.pollen_points).toFixed(2)}
                  </span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-black/50">
                  <div className={cn("h-full rounded-full opacity-95", barColor(idx))} style={{ width: `${w}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

function KpiChip({
  label,
  value,
  delta,
  sub,
}: {
  label: string;
  value: string;
  delta?: number;
  sub?: string;
}) {
  return (
    <article className="rounded-2xl border border-cyan/[0.1] bg-hive-card/90 p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="font-[family-name:var(--font-inter)] text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
        <DollarSignIcon className="h-6 w-6 text-pollen" aria-hidden />
      </div>
      <p className="mt-3 font-[family-name:var(--font-poppins)] text-3xl text-[#fafafa]">{value}</p>
      {typeof delta === "number" && delta !== 0 ? (
        <p className={cn("mt-2 font-[family-name:var(--font-jetbrains-mono)] text-xs", delta > 0 ? "text-success" : "text-danger")}>
          {delta > 0 ? "+" : ""}
          {delta}%
        </p>
      ) : null}
      {sub ? <p className="mt-2 font-[family-name:var(--font-inter)] text-[11px] text-zinc-500">{sub}</p> : null}
    </article>
  );
}
