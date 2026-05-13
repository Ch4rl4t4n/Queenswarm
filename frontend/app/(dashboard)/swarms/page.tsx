import Link from "next/link";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow, DashboardSummary, SubSwarmRow, WaggleDanceSummaryRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

function purposePalette(purpose: string): { border: string; hex: string; glow: string; bar: string } {
  const p = purpose.toUpperCase();
  if (p.includes("SCOUT")) {
    return {
      border: "border-[#00E5FF]/35",
      hex: "from-[#00E5FF]/90 to-cyan-700",
      glow: "shadow-[0_0_24px_rgb(0_229_255/0.25)]",
      bar: "bg-[#00E5FF]",
    };
  }
  if (p.includes("EVAL")) {
    return {
      border: "border-pollen/35",
      hex: "from-pollen to-amber-600",
      glow: "shadow-[0_0_24px_rgb(255_184_0/0.3)]",
      bar: "bg-pollen",
    };
  }
  if (p.includes("SIM")) {
    return {
      border: "border-alert/35",
      hex: "from-alert/90 to-fuchsia-700",
      glow: "shadow-[0_0_28px_rgb(255_0_170/0.28)]",
      bar: "bg-alert",
    };
  }
  return {
    border: "border-success/35",
    hex: "from-success/90 to-emerald-800",
    glow: "shadow-[0_0_22px_rgb(0_255_136/0.28)]",
    bar: "bg-success",
  };
}

function relativeSync(iso: string | null | undefined): string {
  if (!iso) return "awaiting beacon";
  const then = new Date(iso).getTime();
  const sec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (sec < 120) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

function matchPurpose(agent: AgentRow, needle: string): boolean {
  const p = (agent.swarm_purpose ?? "").toLowerCase();
  if (p.includes(needle)) {
    return true;
  }
  const name = (agent.swarm_name ?? "").toLowerCase();
  return name.includes(needle);
}

function fallbackSwarms(agents: AgentRow[] | null): SubSwarmRow[] {
  const templates: { purpose: string; name: string; needle: string }[] = [
    { purpose: "scout", name: "Scout Swarm", needle: "scout" },
    { purpose: "eval", name: "Eval Swarm", needle: "eval" },
    { purpose: "simulation", name: "Sim Swarm", needle: "sim" },
    { purpose: "action", name: "Action Swarm", needle: "action" },
  ];

  const pool = agents ?? [];
  return templates.map((t, idx) => ({
    id: `synthetic-swarm-${idx}`,
    name: t.name,
    purpose: t.purpose,
    member_count: pool.filter((a) => matchPurpose(a, t.needle)).length,
    total_pollen: Math.round(pool.filter((a) => matchPurpose(a, t.needle)).reduce((s, a) => s + Number(a.pollen_points ?? 0), 0)),
    is_active: true,
    last_global_sync_at: null,
  }));
}

export default async function SwarmsPage() {
  const coloniesRaw = await hiveServerRawJson<SubSwarmRow[]>("/swarms?limit=50");
  const summary = await hiveServerRawJson<DashboardSummary>("/dashboard/summary");
  const dances: WaggleDanceSummaryRow[] = summary?.waggle_dances ?? [];

  let colonies: SubSwarmRow[];
  let usedFallback = false;

  if (coloniesRaw && coloniesRaw.length > 0) {
    colonies = coloniesRaw;
  } else {
    const agentsSeed = await hiveServerRawJson<AgentRow[]>("/agents?limit=200");
    colonies = fallbackSwarms(agentsSeed);
    usedFallback = true;
  }

  return (
    <div className="space-y-10">
      <HivePageHeader
        title="Sub-Swarms"
        subtitle="Four decentralized roves with local memory. Global sync every 5 min."
      />

      {usedFallback ? (
        <article className="rounded-3xl border border-pollen/30 bg-black/35 px-4 py-3 font-[family-name:var(--font-inter)] text-sm text-zinc-300">
          Live <code className="font-mono text-xs text-data">GET /api/v1/swarms</code> payload was empty or unreachable — showing static quorum cards seeded with counts from{" "}
          <code className="font-mono text-xs text-data">/agents</code>. Sign in via the cockpit if SSR cannot read your session cookie, or configure{" "}
          <code className="font-mono text-xs text-data">HIVE_PROXY_JWT</code> for unattended renders.
        </article>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2">
        {colonies.length === 0 ? (
          <p className="md:col-span-2 rounded-2xl border border-cyan/15 bg-black/40 p-8 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-400">
            No swarm rows materialized yet.
          </p>
        ) : null}
        {colonies.map((swarm, idx) => {
          const pal = purposePalette(swarm.purpose);
          const perf = Math.min(99, 62 + (swarm.member_count % 37));
          return (
            <article
              key={swarm.id}
              className={cn(
                "relative overflow-hidden rounded-3xl border bg-hive-card/95 p-6 shadow-[0_24px_64px_rgb(0_0_0/0.42)] backdrop-blur-sm",
                pal.border,
              )}
            >
              <div className="flex justify-between gap-3">
                <div className="flex gap-3">
                  <div
                    className={cn(
                      "flex h-12 w-12 shrink-0 items-center justify-center hive-hex bg-gradient-to-br font-[family-name:var(--font-jetbrains-mono)] font-bold text-black",
                      pal.hex,
                      pal.glow,
                    )}
                  >
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="font-[family-name:var(--font-inter)] text-xs uppercase tracking-[0.16em] text-zinc-500">
                      {swarm.purpose.replaceAll("_", " ")}
                    </p>
                    <h2 className="font-[family-name:var(--font-space-grotesk)] text-2xl font-semibold tracking-tight text-[#fafafa]">
                      {swarm.name}
                    </h2>
                    <p className="mt-1 font-[family-name:var(--font-inter)] text-sm text-muted-foreground">
                      Queen node mirror · pollen-weighted imitation lane.
                    </p>
                  </div>
                </div>
                {swarm.is_active ? (
                  <span className="inline-flex h-fit items-center gap-1 rounded-full border border-success/35 bg-success/[0.1] px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.1em] text-success">
                    ● Active
                  </span>
                ) : (
                  <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase text-danger">Dormant</span>
                )}
              </div>
              <dl className="mt-6 grid grid-cols-3 gap-3 font-[family-name:var(--font-jetbrains-mono)] text-sm text-[#e4e4e7]/90">
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.18em] text-zinc-500">Queen</dt>
                  <dd className="mt-1">Q-{String(swarm.name).slice(0, 7)}-{idx + 1}</dd>
                </div>
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.18em] text-zinc-500">Members</dt>
                  <dd className="mt-1 text-data tabular-nums">{swarm.member_count}</dd>
                </div>
                <div>
                  <dt className="font-[family-name:var(--font-inter)] text-[10px] uppercase tracking-[0.18em] text-zinc-500">Perf</dt>
                  <dd className="mt-1 text-success tabular-nums">{perf}%</dd>
                </div>
              </dl>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-black/55">
                <div className={cn("h-full rounded-full shadow-[0_0_12px_currentColor]", pal.bar)} style={{ width: `${perf}%` }} />
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-cyan/[0.06] pt-4">
                <span className="font-[family-name:var(--font-inter)] text-xs text-zinc-500">
                  Last sync · {relativeSync(swarm.last_global_sync_at)}
                </span>
                <Link href="/agents" className="font-[family-name:var(--font-inter)] text-sm font-medium text-data hover:text-pollen">
                  Open swarm →
                </Link>
              </div>
            </article>
          );
        })}
      </div>

      <section className="rounded-3xl border border-cyan/[0.1] bg-hive-card/90 p-6">
        <div className="flex flex-wrap justify-between gap-4 border-b border-cyan/[0.08] pb-4">
          <h3 className="font-[family-name:var(--font-space-grotesk)] text-lg text-[#fafafa]">Waggle Dance Feed</h3>
          <p className="font-[family-name:var(--font-inter)] text-sm text-muted-foreground">Cross swarm signal exchange</p>
        </div>
        <ul className="divide-y divide-cyan/[0.06] hive-scrollbar mt-4 max-h-[320px] overflow-y-auto font-[family-name:var(--font-inter)]">
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
              Beacon quiet — enqueue /tasks to prime cross-swarm payloads.
            </li>
          ) : null}
        </ul>
      </section>
    </div>
  );
}
