import Link from "next/link";

import { NeonButton } from "@/components/ui/neon-button";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { HiveCostSummary } from "@/lib/hive-dashboard-session";

export const dynamic = "force-dynamic";

export default async function SettingsBillingPage() {
  const cost = await hiveServerRawJson<HiveCostSummary>("/dashboard/cost-summary");

  const cap = cost?.monthly_budget_cap_usd ?? 500;
  const used = cost?.spent_usd_rolling_30d ?? 0;
  const pct = Math.min(100, cap > 0 ? Math.round((used / cap) * 100) : 0);
  const warnRatio = cost?.cost_warning_threshold ?? 0.8;

  const warnLine =
    pct >= warnRatio * 100 ? (
      <p className="mt-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-alert">
        Prekročený governor prah {(warnRatio * 100).toFixed(0)}% · skontroluj Cost Governor.
      </p>
    ) : null;

  return (
    <article className="rounded-2xl border border-cyan/[0.12] bg-hive-card/90 p-6 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#fafafa]">
            Spend · Cost Governor
          </h2>
          <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
            Rolling 30d LLM zápis z cost_records ↔ env limity Queenswarm Governor.
          </p>
          {!cost ? (
            <p className="mt-4 text-xs text-alert">Nepodarilo sa načítať /dashboard/cost-summary.</p>
          ) : null}
        </div>
        <NeonButton variant="ghost" className="text-xs" asChild>
          <Link href="/costs">Otvoriť Costs</Link>
        </NeonButton>
      </div>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div>
          <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">Monthly cap (.env)</p>
          <p className="mt-2 font-[family-name:var(--font-space-grotesk)] text-2xl text-pollen">${cap.toFixed(2)}</p>
          <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-500">
            Daily ${(cost?.daily_budget_usd ?? 0).toFixed(2)} · Weekly ${(cost?.weekly_budget_usd ?? 0).toFixed(2)}
          </p>
        </div>
        <div className="text-right sm:text-left">
          <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">Spent rolling 30d</p>
          <p className="mt-2 font-[family-name:var(--font-space-grotesk)] text-2xl text-[#fafafa]">
            ${used.toFixed(2)}
          </p>
          <p className="mt-1 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">{pct}% of cap</p>
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-black/50">
        <div
          className={
            pct >= warnRatio * 100
              ? "h-full rounded-full bg-gradient-to-r from-alert to-[#FF00AA] shadow-[0_0_14px_rgb(255_0_170/0.45)]"
              : "h-full rounded-full bg-gradient-to-r from-pollen to-amber-500 shadow-[0_0_12px_rgb(255_184_0/0.35)]"
          }
          style={{ width: `${pct}%` }}
        />
      </div>

      {warnLine}

      <p className="mt-3 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-600">
        {cost?.window_started_at ? `Window start: ${cost.window_started_at}` : ""}
      </p>
    </article>
  );
}
