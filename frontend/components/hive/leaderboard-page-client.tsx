"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HexNumberBadge } from "@/components/hive/hex-metric-tile";
import { V4PageCanvas } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { AgentRow, RecipeRow, SubSwarmRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type LeaderTab = "agents" | "swarms" | "recipes";

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

/** Tabbed prestige boards backed by live API sorts — sticky controls on mobile. */
export function LeaderboardPageClient() {
  const [tab, setTab] = useState<LeaderTab>("agents");
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [swarms, setSwarms] = useState<SubSwarmRow[]>([]);
  const [recipes, setRecipes] = useState<RecipeRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    void Promise.all([
      hiveGet<AgentRow[]>("agents?limit=160"),
      hiveGet<SubSwarmRow[]>("swarms?limit=120"),
      hiveGet<RecipeRow[]>("recipes?verified_only=true&limit=120"),
    ])
      .then(([a, sw, rc]) => {
        if (cancelled) return;
        setAgents(a);
        setSwarms(sw);
        setRecipes(rc);
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof HiveApiError ? e.message : "Leaderboard data unavailable.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rankedAgents = useMemo(() => [...agents].sort((x, y) => y.pollen_points - x.pollen_points).slice(0, 12), [agents]);

  const rankedSwarms = useMemo(() => [...swarms].sort((x, y) => y.total_pollen - x.total_pollen).slice(0, 12), [swarms]);

  const rankedRecipes = useMemo(
    () => [...recipes].sort((x, y) => (y.success_count ?? 0) - (x.success_count ?? 0)).slice(0, 12),
    [recipes],
  );

  const tabs: { id: LeaderTab; label: string }[] = [
    { id: "agents", label: "Agents" },
    { id: "swarms", label: "Swarms" },
    { id: "recipes", label: "Recipes" },
  ];

  return (
    <V4PageCanvas className="gap-8">
      <HivePageHeader title="Leaderboard" subtitle="Pollen-first bees · colony pollen totals · recipe win counts — live sorts." />

      <nav aria-label="Leaderboard scope" className="v4-subtab-row w-full max-w-full">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn("v4-subtab min-h-[42px] touch-manipulation", tab === id && "v4-subtab--active")}
          >
            {label}
          </button>
        ))}
      </nav>

      {err ? (
        <p className="rounded-xl border border-danger/35 bg-black/45 px-4 py-3 font-[family-name:var(--font-poppins)] text-sm text-danger">{err}</p>
      ) : null}

      <div className="v4-leaderboard-layout grid gap-6">
        <section className="v4-leaderboard-panel rounded-3xl border border-[color:var(--qs-border)] bg-hive-card/95 p-4 md:p-6">
          <div className="flex justify-between gap-4 border-b border-[color:var(--qs-border-2)]/[0.08] pb-4 font-[family-name:var(--font-poppins)]">
            <h2 className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">
              {tab === "agents" ? "Top bees" : tab === "swarms" ? "Top colonies" : "Top recipes"}
            </h2>
            <span className="text-xs text-muted-foreground">
              {tab === "agents" ? "Pollen points" : tab === "swarms" ? "Colony pollen" : "Verified wins"}
            </span>
          </div>

          {tab === "agents" ? (
            <ol className="mt-6 space-y-4 font-[family-name:var(--font-poppins)]">
              {rankedAgents.map((agent, idx) => (
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
                  <Link href={`/agents/${encodeURIComponent(agent.id)}`} className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-[#fafafa] hover:text-pollen">{agent.name}</p>
                    <p className="truncate text-xs text-zinc-500">{agent.role.replaceAll("_", " ")}</p>
                  </Link>
                  <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-pollen/30 bg-black/45 px-2 py-1 font-[family-name:var(--font-poppins)] text-xs text-pollen">
                    {Math.round(agent.pollen_points)}
                  </span>
                </li>
              ))}
            </ol>
          ) : null}

          {tab === "swarms" ? (
            <ol className="mt-6 space-y-4 font-[family-name:var(--font-poppins)]">
              {rankedSwarms.map((swarm, idx) => (
                <li key={swarm.id} className="flex items-center gap-3">
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
                    <p className="truncate font-semibold text-[#fafafa]">{swarm.name}</p>
                    <p className="truncate text-xs uppercase tracking-[0.14em] text-zinc-500">{swarm.purpose}</p>
                  </div>
                  <span className="inline-flex shrink-0 rounded-full border border-[color:var(--qs-border-2)] bg-black/45 px-2 py-1 font-mono text-xs text-cyan">
                    {Math.round(swarm.total_pollen)}
                  </span>
                </li>
              ))}
            </ol>
          ) : null}

          {tab === "recipes" ? (
            <ol className="mt-6 space-y-4 font-[family-name:var(--font-poppins)]">
              {rankedRecipes.map((recipe, idx) => (
                <li key={recipe.id} className="flex items-center gap-3">
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
                    <p className="truncate font-semibold text-[#fafafa]">{recipe.name}</p>
                    <p className="truncate text-xs text-zinc-500">avg pollen {Math.round(recipe.avg_pollen_earned ?? 0)}</p>
                  </div>
                  <span className="inline-flex shrink-0 rounded-full border border-success/35 bg-black/45 px-2 py-1 text-xs text-success">
                    {recipe.success_count ?? 0} wins
                  </span>
                </li>
              ))}
            </ol>
          ) : null}
        </section>

        <section className="v4-leaderboard-panel rounded-3xl border border-[color:var(--qs-border)] bg-hive-card/95 p-4 md:p-6">
          <div className="border-b border-[color:var(--qs-border-2)]/[0.08] pb-4 font-[family-name:var(--font-poppins)]">
            <h2 className="text-lg text-[#fafafa]">Hive prestige notes</h2>
            <p className="mt-2 text-xs text-muted-foreground">
              Desktop column highlights interpretability — mobile stacks below the ranking list for minimal horizontal scrolling.
            </p>
          </div>
          <ul className="mt-6 space-y-3 font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
            <li>• Agents rank by live pollen ledger — tie-breaker is API insertion order.</li>
            <li>• Swarms use ``total_pollen`` captured during sub-swarm sync cadence.</li>
            <li>• Recipes prioritize verified ``success_count`` for imitation readiness.</li>
          </ul>
        </section>
      </div>
    </V4PageCanvas>
  );
}
