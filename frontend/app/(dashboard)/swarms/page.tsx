import { SwarmManagerConsole } from "@/components/hive/swarm-manager-console";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { DashboardSummary, WaggleDanceSummaryRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

function relativeSync(iso: string | null | undefined): string {
  if (!iso) return "awaiting beacon";
  const then = new Date(iso).getTime();
  const sec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (sec < 120) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

export default async function SwarmsPage() {
  const summary = await hiveServerRawJson<DashboardSummary>("/dashboard/summary");
  const dances: WaggleDanceSummaryRow[] = summary?.waggle_dances ?? [];

  return (
    <div className="space-y-10">
      <HivePageHeader
        title="Sub-Swarms"
        subtitle="Create colonies, anchor bees, and wake offline workers. Global sync cadence unchanged."
      />

      <SwarmManagerConsole />

      <section className="rounded-3xl border border-cyan/[0.1] bg-hive-card/90 p-6">
        <div className="flex flex-wrap justify-between gap-4 border-b border-cyan/[0.08] pb-4">
          <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg text-[#fafafa]">Waggle Dance Feed</h3>
          <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">Cross swarm signal exchange</p>
        </div>
        <ul className="hive-scrollbar mt-4 max-h-[320px] divide-y divide-cyan/[0.06] overflow-y-auto font-[family-name:var(--font-inter)]">
          {dances.slice(0, 12).map((row: WaggleDanceSummaryRow) => (
            <li key={`${row.ts}-${row.from_swarm}-${row.signal}`} className="flex flex-wrap items-center gap-4 py-3 text-sm">
              <span className="rounded-full border border-data/30 bg-black/35 px-2 py-1 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-data">
                [{row.from_swarm}]
              </span>
              <span aria-hidden className="text-muted-foreground">
                →
              </span>
              <span className="text-[#fafafa]">
                {row.signal}: {row.topic}
              </span>
              <span className="ml-auto font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">{relativeSync(row.ts)}</span>
            </li>
          ))}
          {dances.length === 0 ? (
            <li className="py-10 text-center text-sm text-muted-foreground">
              Beacon quiet — enqueue `/tasks/new` to prime cross-swarm payloads.
            </li>
          ) : null}
        </ul>
      </section>
    </div>
  );
}
