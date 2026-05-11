import { BotIcon, BoxIcon, DatabaseIcon } from "lucide-react";

import { AgentHexCard } from "@/components/hive/agent-hex-card";
import { DanceStrip } from "@/components/hive/dance-strip";
import { LivePulse } from "@/components/hive/live-pulse";
import { WidgetStat } from "@/components/hive/widget-stat";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, DashboardSummary } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

function statusBreakdown(summary: DashboardSummary["agents"]) {
  return Object.entries(summary.by_status)
    .map(([k, v]) => `${k}: ${v}`)
    .slice(0, 6)
    .join(" · ");
}

export default async function HiveHomeDashboard() {
  const summary = await hiveServerRawJson<DashboardSummary>("/dashboard/summary");
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=8");

  if (!summary) {
    return (
      <div className="rounded-3xl border border-danger bg-black/55 p-8 text-danger">
        <p className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-pollen">
          dashboard offline
        </p>
        <p className="mt-4 font-[family-name:var(--font-jetbrains-mono)] text-sm">
          Set INTERNAL_BACKEND_ORIGIN and HIVE_PROXY_JWT / DASHBOARD_JWT inside the frontend container · API must accept
          the proxy bearer token.
        </p>
      </div>
    );
  }

  const bees = agents ?? [];

  return (
    <div className="space-y-12">
      <header className="space-y-3">
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.32em] text-cyan">
          neon.hive · queenswarm cognitive os
        </p>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-4xl font-semibold tracking-tight text-pollen shadow-[0_0_54px_rgba(255,184,0,0.54)] md:text-5xl">
          command waggle lattice
        </h1>
        <p className="max-w-3xl font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#CBFFFF]/90">
          {statusBreakdown(summary.agents)} · swarms carry local hive minds syncing into the planetary ledger every ~
          five minutes · only verified payloads reach operators.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <WidgetStat
          icon={BotIcon}
          label="active colony bees"
          value={String(summary.agents.total)}
          caption={`queue depth · ${summary.tasks.pending} pending`}
        />
        <WidgetStat
          icon={DatabaseIcon}
          label={`pollen (last ${summary.pollen.window_hours}h)`}
          value={`${summary.pollen.earned_last_24h.toFixed(2)} μ`}
          caption={`system Σ pollen · ${summary.pollen.system_total_estimate.toFixed(2)}`}
        />
        <WidgetStat
          icon={BoxIcon}
          label="verified recipes online"
          value={String(summary.recipes.total)}
          caption={`sub-swarms ${summary.swarms.total}`}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-5">
        <div className="space-y-4 xl:col-span-3">
          <h2 className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-data">
            hot bees (hex occupancy)
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {bees.slice(0, 8).map((bee) => (
              <AgentHexCard key={bee.id} agent={bee} />
            ))}
          </div>
          {bees.length === 0 ? (
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-cyan/60">
              awaiting agents · run hive_seed.py inside backend once databases are warm.
            </p>
          ) : null}
        </div>
        <div className="space-y-6 xl:col-span-2">
          <LivePulse />
          <DanceStrip dances={summary.waggle_dances} />
        </div>
      </section>

      <section className="rounded-3xl border border-cyan/15 bg-black/35 p-6">
        <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-pollen">
          imitation radar (top pollen)
        </h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {summary.leaderboard_preview.slice(0, 6).map((row) => (
            <div key={row.agent_id} className="rounded-2xl border border-pollen/35 bg-black/45 p-4">
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-cyan">
                #{row.rank} · {row.role}
              </p>
              <p className="font-[family-name:var(--font-space-grotesk)] text-xl font-semibold text-pollen">{row.name}</p>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#00FF88]">
                pollen {row.pollen.toFixed(3)} · τ {row.performance.toFixed(2)}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
