import { PollenRankChart } from "@/components/hive/pollen-bar-chart";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { DashboardSummary } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function CostsPage() {
  const summary = await hiveServerRawJson<DashboardSummary>("/dashboard/summary");

  if (!summary) {
    return (
      <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">
        Need dashboard aggregates to plot spend proxies — backend offline or bearer misconfigured.
      </p>
    );
  }

  const chartPayload = summary.leaderboard_preview.map((agent) => ({
    label:
      agent.name.length > 14
        ? `${agent.name.slice(0, 12)}…`
        : agent.name,
    pollen: agent.pollen,
  }));

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-4xl font-semibold text-pollen">
          cost pollen telemetry
        </h1>
        <p className="mt-4 max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm leading-relaxed text-cyan">
          CostGovernor enforces LiteLLM daily envelopes server-side (default USD 10/day via env DAILY_BUDGET_USD) while
          Prometheus increments <span className="text-pollen">queenswarm_budget_blocks_total</span> whenever burns would overshoot
          the cap. Bars below correlate pollen hotspots with imitation pressure.
        </p>
      </header>
      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-3xl border border-cyan/30 bg-black/35 p-5">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.25em] text-muted-foreground">
            pollen in last window
          </p>
          <p className="mt-4 font-[family-name:var(--font-space-grotesk)] text-4xl text-success">
            {summary.pollen.earned_last_24h.toFixed(2)}
          </p>
        </article>
        <article className="rounded-3xl border border-cyan/30 bg-black/35 p-5">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.25em] text-muted-foreground">
            system pollen ledger
          </p>
          <p className="mt-4 font-[family-name:var(--font-space-grotesk)] text-4xl text-[#FFB800]">
            {summary.pollen.system_total_estimate.toFixed(2)}
          </p>
        </article>
        <article className="rounded-3xl border border-cyan/30 bg-black/35 p-5">
          <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.25em] text-muted-foreground">
            Grafana & Prometheus
          </p>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Visit `/grafana/` for Hive dashboard + alertmanager hooks once SMTP is configured for ops notifications.
          </p>
        </article>
      </section>

      <section>
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-2xl text-data">leaderboard pollen heat</h2>
        <PollenRankChart data={chartPayload.length ? chartPayload : [{ label: "idle", pollen: 0 }]} />
      </section>
    </div>
  );
}
