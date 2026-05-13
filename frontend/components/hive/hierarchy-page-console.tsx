"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HexAgentCard } from "@/components/hive/hex-agent-card";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface SwarmBrief {
  id: string;
  name: string;
  purpose?: string;
  local_memory?: Record<string, unknown> | null;
  queen_agent_id?: string | null;
}

const GAP_HEX = 18;
/** Same footprint as Agents grid `HexAgentCard` default — keeps hex stroke + layout identical to roster. */
const TILE_HEX = 140;
const WORKERS_PER_ROW = 4;

function coerceAgent(raw: Record<string, unknown>): AgentRow {
  return {
    id: typeof raw.id === "string" ? raw.id : raw.id !== undefined && raw.id !== null ? String(raw.id) : "",
    name: typeof raw.name === "string" ? raw.name : "Agent",
    role: typeof raw.role === "string" ? raw.role : "WORKER",
    status: typeof raw.status === "string" ? raw.status : "IDLE",
    pollen_points: Number(raw.pollen_points ?? 0),
    performance_score: typeof raw.performance_score === "number" ? raw.performance_score : undefined,
    swarm_id:
      raw.swarm_id !== undefined && raw.swarm_id !== null && String(raw.swarm_id).trim()
        ? String(raw.swarm_id)
        : null,
    sub_swarm_id:
      raw.sub_swarm_id !== undefined && raw.sub_swarm_id !== null && String(raw.sub_swarm_id).trim()
        ? String(raw.sub_swarm_id)
        : null,
    swarm_type: typeof raw.swarm_type === "string" ? raw.swarm_type : null,
    swarm:
      typeof raw.swarm === "object" && raw.swarm !== null ? (raw.swarm as { name?: string }) : null,
    swarm_name: typeof raw.swarm_name === "string" ? raw.swarm_name : null,
    swarm_purpose: typeof raw.swarm_purpose === "string" ? raw.swarm_purpose : null,
    hive_tier: typeof raw.hive_tier === "string" ? raw.hive_tier : null,
  };
}

function displaySwarmColor(sw: SwarmBrief): string {
  const lm = sw.local_memory ?? {};
  const hi = (lm.hive_ui as Record<string, unknown> | undefined) ?? {};
  const hex = (hi.swarm_color_hex as string) || (lm.swarm_color_hex as string);
  if (typeof hex === "string" && hex.startsWith("#")) {
    return hex;
  }
  const p = String(sw.purpose ?? "").toLowerCase();
  if (p.includes("scout")) return "#00E5FF";
  if (p.includes("eval")) return "#FFB800";
  if (p.includes("sim")) return "#FF00AA";
  return "#00FF88";
}

/** Trunk / branch connectors (same palette as Agents hex stroke). */
function VLine({ color, h }: { color: string; h: number }): JSX.Element {
  return (
    <div
      className="mx-auto shrink-0 rounded-[1px]"
      style={{
        width: 2,
        height: h,
        background: `linear-gradient(to bottom, ${color}88, ${color}33)`,
      }}
      aria-hidden
    />
  );
}

function HLine({ widthPx, color }: { widthPx: number; color: string }): JSX.Element {
  return (
    <div
      className="mx-auto shrink-0 rounded-[1px]"
      style={{
        height: 2,
        width: Math.max(0, widthPx),
        background: `linear-gradient(to right, ${color}33, ${color}88, ${color}33)`,
      }}
      aria-hidden
    />
  );
}

function chunkRows<T>(items: T[], perRow: number): T[][] {
  return Array.from({ length: Math.ceil(items.length / perRow) }, (_, i) => items.slice(i * perRow, i * perRow + perRow));
}

/** Hierarchy route — same `HexAgentCard` tiles + CSS as Agents; explicit Queen → managers → workers tree. */
export function HierarchyPageConsole(): JSX.Element {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [swarms, setSwarms] = useState<SwarmBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    void Promise.allSettled([
      fetch("/api/proxy/agents?limit=200", { credentials: "include" }).then((r) => (r.ok ? r.json() : null)),
      fetch("/api/proxy/swarms?limit=200", { credentials: "include" }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([ar, sr]) => {
        if (!alive) {
          return;
        }
        if (ar.status === "fulfilled" && ar.value && typeof ar.value === "object") {
          const obj = ar.value as Record<string, unknown>;
          const list = (Array.isArray(ar.value)
            ? ar.value
            : Array.isArray(obj.agents)
              ? obj.agents
              : Array.isArray(obj.items)
                ? obj.items
                : []) as Record<string, unknown>[];
          setAgents(list.map(coerceAgent).filter((a) => a.id));
        }
        if (sr.status === "fulfilled" && sr.value && typeof sr.value === "object") {
          const obj = sr.value as Record<string, unknown>;
          const list = (Array.isArray(sr.value)
            ? sr.value
            : Array.isArray(obj.swarms)
              ? obj.swarms
              : Array.isArray(obj.items)
                ? obj.items
                : []) as Record<string, unknown>[];
          setSwarms(
            list
              .filter((s) => s && typeof s === "object" && "id" in s && "name" in s)
              .map((s) => {
                const row = s as Record<string, unknown>;
                return {
                  id: String(row.id),
                  name: String(row.name),
                  purpose: typeof row.purpose === "string" ? row.purpose : undefined,
                  local_memory: (row.local_memory as Record<string, unknown> | null) ?? null,
                  queen_agent_id:
                    row.queen_agent_id !== undefined && row.queen_agent_id !== null
                      ? String(row.queen_agent_id)
                      : null,
                } satisfies SwarmBrief;
              }),
          );
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const tree = useMemo(() => {
    const orchestrator: AgentRow[] = [];
    const tierManagers: AgentRow[] = [];
    const tierWorkers: AgentRow[] = [];
    const unknown: AgentRow[] = [];
    for (const row of agents) {
      const tier = (row.hive_tier ?? "").toLowerCase();
      if (tier === "orchestrator") {
        orchestrator.push(row);
      } else if (tier === "manager") {
        tierManagers.push(row);
      } else if (tier === "worker") {
        tierWorkers.push(row);
      } else {
        unknown.push(row);
      }
    }
    const byQueenSwarm = new Set(swarms.map((s) => s.queen_agent_id).filter((x): x is string => Boolean(x)));
    const inferredManagers = agents.filter(
      (a) =>
        !orchestrator.some((q) => q.id === a.id) &&
        (byQueenSwarm.has(a.id) ||
          a.name.toLowerCase().includes("manager") ||
          a.role.toLowerCase().includes("manager")),
    );
    const queen: AgentRow | null =
      orchestrator[0] ??
      agents.find(
        (a) =>
          a.name.toLowerCase().includes("orchestrat") ||
          a.role.toLowerCase().includes("orchestrat") ||
          a.role.toLowerCase().includes("queen"),
      ) ??
      agents[0] ??
      null;
    const queenId = queen?.id;
    const managerList: AgentRow[] = [];
    const seen = new Set<string>();
    for (const m of [...tierManagers, ...inferredManagers]) {
      if (queenId && m.id === queenId) continue;
      if (!seen.has(m.id)) {
        seen.add(m.id);
        managerList.push(m);
      }
    }
    const pool = [...tierWorkers, ...unknown];
    const teamByManager = new Map<string, AgentRow[]>();
    for (const m of managerList) {
      teamByManager.set(m.id, []);
    }
    const ungrouped: AgentRow[] = [];
    for (const w of pool) {
      const sid = w.swarm_id ?? w.sub_swarm_id;
      let assigned = false;
      if (sid) {
        for (const m of managerList) {
          if (m.swarm_id && m.swarm_id === sid) {
            teamByManager.get(m.id)!.push(w);
            assigned = true;
            break;
          }
          const sw = swarms.find((s) => s.queen_agent_id === m.id);
          if (sw && sw.id === sid) {
            teamByManager.get(m.id)!.push(w);
            assigned = true;
            break;
          }
        }
      }
      if (!assigned) ungrouped.push(w);
    }
    return { queen, managers: managerList, teamByManager, ungrouped };
  }, [agents, swarms]);

  if (loading) {
    return (
      <div className="py-16 text-center font-mono text-sm text-[var(--qs-text-3)]">Načítavam hierarchiu…</div>
    );
  }

  const amber = "#FFB800";
  const managerBridgeWidth =
    tree.managers.length > 1 ? (tree.managers.length - 1) * (TILE_HEX + GAP_HEX) : 0;

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Hierarchia úľa"
        subtitle="Queen riadi manažérov · rovnaké hex dlaždice (140 px) ako na Agents · queen zlatý rám + koruna."
      />

      <div className={cn("flex flex-col items-center pb-14")}>
        {tree.queen ? (
          <>
            <HexAgentCard agent={tree.queen} href={`/agents/${tree.queen.id}`} isQueen tilePx={TILE_HEX} />
            {(tree.managers.length > 0 || tree.ungrouped.length > 0) && <VLine color={amber} h={44} />}
          </>
        ) : agents.length === 0 ? (
          <div className="px-6 py-14 text-center">
            <div className="mb-3 text-5xl">🐝</div>
            <p className="text-sm text-[var(--qs-text-3)]">
              Zatiaľ žiadni agenti —{" "}
              <Link href="/agents/new" className="font-semibold text-[var(--qs-amber)] underline-offset-2 hover:underline">
                spawn prvého agenta
              </Link>
              .
            </p>
          </div>
        ) : (
          <p className="text-center font-mono text-sm text-[var(--qs-text-3)]">
            Žiadny orchestrátor v dátach — označ Hive tier alebo spawn „Queen“ cez Agents.
          </p>
        )}

        {tree.managers.length > 0 ? (
          <div className="flex w-full max-w-[1200px] flex-col items-center">
            {tree.managers.length > 1 ? <HLine widthPx={managerBridgeWidth} color={amber} /> : null}

            <div
              className="relative z-[1] flex flex-wrap justify-center gap-[18px]"
              style={{ marginTop: tree.managers.length > 1 ? 0 : 0 }}
            >
              {tree.managers.map((mgr) => {
                const mgrSwarm =
                  swarms.find((s) => s.queen_agent_id === mgr.id) ??
                  (mgr.swarm_id ? swarms.find((s) => s.id === mgr.swarm_id) : undefined);
                const accent = mgrSwarm ? displaySwarmColor(mgrSwarm) : amber;
                const team = tree.teamByManager.get(mgr.id) ?? [];
                const workerRowSpan = Math.min(team.length, WORKERS_PER_ROW);
                const workerHWidth = team.length > 1 ? (workerRowSpan - 1) * (TILE_HEX + GAP_HEX) : 0;

                return (
                  <div key={mgr.id} className="flex flex-col items-center">
                    <HexAgentCard agent={mgr} href={`/agents/${mgr.id}`} tilePx={TILE_HEX} />
                    {team.length > 0 ? (
                      <>
                        <VLine color={accent} h={32} />
                        {team.length > 1 ? <HLine widthPx={workerHWidth} color={accent} /> : null}
                        <div className="flex flex-col items-center gap-2.5" style={{ marginTop: 0 }}>
                          {chunkRows(team, WORKERS_PER_ROW).map((row) => (
                            <div key={row.map((x) => x.id).join("-")} className="flex flex-wrap justify-center gap-[18px]">
                              {row.map((w) => (
                                <HexAgentCard key={w.id} agent={w} href={`/agents/${w.id}`} tilePx={TILE_HEX} />
                              ))}
                            </div>
                          ))}
                        </div>
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {tree.ungrouped.length > 0 ? (
          <div className="mt-12 w-full max-w-[1200px] px-2">
            <p className="mb-5 text-center font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--qs-text-3)]">
              Robotníci mimo tímov ({tree.ungrouped.length})
            </p>
            <div className="flex flex-wrap justify-center gap-[18px]">
              {tree.ungrouped.map((w) => (
                <HexAgentCard key={w.id} agent={w} href={`/agents/${w.id}`} tilePx={TILE_HEX} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
