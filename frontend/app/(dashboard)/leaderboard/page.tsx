import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HexNumberBadge } from "@/components/hive/hex-metric-tile";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

const PEERS = [
  { label: "Action-01", sub: "Action", bubble: "h-14 w-14 rounded-full bg-gradient-to-br from-emerald-500 to-[#00ff88]" },
  { label: "Eval-01", sub: "Eval", bubble: "h-14 w-14 rounded-full bg-gradient-to-br from-pollen to-amber-800" },
  { label: "Scout-01", sub: "Scout", bubble: "h-14 w-14 rounded-full bg-gradient-to-br from-cyan-400 to-data" },
  { label: "Sim-02", sub: "Sim", bubble: "h-14 w-14 rounded-full bg-gradient-to-br from-fuchsia-500 to-alert" },
] as const;

const RANK_PODIUM = [
  { stroke: "#FACC15", variant: "solid" as const },
  { stroke: "#E2E8F0", variant: "solid" as const },
  { stroke: "#FB923C", variant: "solid" as const },
];

function rankHexProps(idx: number): { strokeColor: string; variant: "solid" | "default"; glowColor?: string } {
  if (idx < 3) {
    const p = RANK_PODIUM[idx]!;
    return { strokeColor: p.stroke, variant: p.variant, glowColor: p.stroke };
  }
  return { strokeColor: "#71717A", variant: "default" };
}

export default async function LeaderboardPage() {
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=120");

  if (!agents) {
    return <p className="text-sm font-[family-name:var(--font-poppins)] text-danger">Agent telemetry unavailable.</p>;
  }

  const ranked = [...agents].sort((a, b) => b.pollen_points - a.pollen_points).slice(0, 8);

  return (
    <div className="space-y-10">
      <HivePageHeader
        title="Leaderboard"
        subtitle="Agents · Swarms · Recipes imitate graph — pollen-weighted prestige."
      />

      <nav className="-mt-6 flex w-full gap-2 overflow-x-auto hive-scrollbar rounded-xl border border-cyan/[0.1] bg-black/35 p-1 font-[family-name:var(--font-poppins)] text-sm md:w-fit">
        {["Agents", "Swarms", "Recipes"].map((lab, idx) => (
          <button
            key={lab}
            type="button"
            className={cn(
              "shrink-0 rounded-lg px-4 py-1.5",
              idx === 0 ? "bg-pollen/[0.15] font-semibold text-pollen shadow-[inset_0_0_0_1px_rgb(255_184_0/0.3)]" : "text-zinc-500 hover:text-[#fafafa]",
            )}
          >
            {lab}
          </button>
        ))}
      </nav>

      <div className="grid gap-6 xl:grid-cols-5">
        <section className="rounded-3xl border border-cyan/[0.1] bg-hive-card/95 p-6 xl:col-span-2">
          <div className="flex justify-between gap-4 border-b border-cyan/[0.08] pb-4 font-[family-name:var(--font-poppins)]">
            <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">Top bees · this week</h2>
            <span className="text-xs text-muted-foreground">By pollen earned</span>
          </div>
          <ol className="mt-6 space-y-4 font-[family-name:var(--font-poppins)]">
            {ranked.map((agent, idx) => (
              <li key={agent.id} className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center" aria-hidden>
                  {(() => {
                    const r = rankHexProps(idx);
                    return (
                      <HexNumberBadge
                        value={idx + 1}
                        strokeColor={r.strokeColor}
                        variant={r.variant}
                        glowColor={r.glowColor}
                        sizePx={idx < 3 ? 42 : 38}
                      />
                    );
                  })()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-[#fafafa]">{agent.name}</p>
                  <p className="truncate text-xs text-zinc-500">{agent.role.replaceAll("_", " ")}</p>
                </div>
                <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-pollen/30 bg-black/45 px-2 py-1 font-[family-name:var(--font-poppins)] text-xs text-pollen">
                  {Math.round(agent.pollen_points)}
                </span>
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-3xl border border-cyan/[0.1] bg-hive-card/95 p-6 xl:col-span-3">
          <div className="flex justify-between gap-4 border-b border-cyan/[0.08] pb-4 font-[family-name:var(--font-poppins)]">
            <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">Imitation network</h2>
            <span className="text-xs text-muted-foreground">Who copies whom</span>
          </div>
          <div className="mt-8 flex flex-col items-center gap-10 py-4">
            <div className="flex flex-col items-center gap-2">
              <div className="h-24 w-24 rounded-full bg-gradient-to-br from-pollen to-[#FF6B9D] shadow-[0_0_48px_rgb(255_184_0/0.45)] ring-4 ring-black/60" aria-hidden />
              <div className="text-center">
                <p className="font-[family-name:var(--font-poppins)] font-semibold text-[#fafafa]">Queen</p>
                <p className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.2em] text-zinc-500">Hive · coordinator</p>
              </div>
            </div>
            <div className="relative w-full rounded-3xl border border-cyan/[0.06] bg-black/30 p-6">
              <p className="mb-6 text-center font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.22em] text-cyan/50">
                Radiating imitate edges
              </p>
              <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                {PEERS.map((node) => (
                  <div key={node.label} className="flex flex-col items-center gap-2">
                    <div className={`${node.bubble} ring-4 ring-black/70 shadow-[0_0_16px_rgb(0_255_255/0.12)]`} />
                    <div className="text-center">
                      <p className="font-[family-name:var(--font-poppins)] text-[11px] font-semibold text-[#fafafa]">{node.label}</p>
                      <p className="font-[family-name:var(--font-poppins)] text-[9px] uppercase tracking-[0.18em] text-zinc-500">
                        {node.sub}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <svg aria-hidden className="pointer-events-none absolute left-1/2 top-[18%] h-44 w-[90%] -translate-x-1/2 overflow-visible text-pollen/[0.12]">
                <line x1="50%" y1="40%" x2="15%" y2="100%" strokeWidth="2" stroke="currentColor" strokeDasharray="5 14" />
                <line x1="50%" y1="40%" x2="86%" y2="100%" strokeWidth="2" stroke="currentColor" strokeDasharray="5 14" />
              </svg>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
