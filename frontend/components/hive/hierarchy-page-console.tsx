"use client";

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
      typeof raw.swarm === "object" && raw.swarm !== null
        ? (raw.swarm as { name?: string })
        : null,
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

function VerticalRule({ color, h = 32 }: { color: string; h?: number }) {
  return (
    <div className={cn("mx-auto w-0.5 rounded-full opacity-60")} style={{ height: h, backgroundColor: color }} aria-hidden />
  );
}

/** Standalone hierarchy route — same hex tiles as Agents, tree layout (Queen → managers → workers). */
export function HierarchyPageConsole() {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [swarms, setSwarms] = useState<SwarmBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    void Promise.allSettled([
      fetch("/api/proxy/agents?limit=200", { credentials: "include" }).then((r) => (r.ok ? r.json() : null)),
      fetch("/api/proxy/swarms?limit=200", { credentials: "include" }).then((r) => (r.ok ? r.json() : null)),
    ]).then(([ar, sr]) => {
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
    }).finally(() => {
      if (alive) {
        setLoading(false);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  const tree = useMemo(() => {
    const orchestrator: AgentRow[] = [];
    const managers: AgentRow[] = [];
    const workers: AgentRow[] = [];
    const unknown: AgentRow[] = [];
    for (const row of agents) {
      const tier = (row.hive_tier ?? "").toLowerCase();
      if (tier === "orchestrator") {
        orchestrator.push(row);
      } else if (tier === "manager") {
        managers.push(row);
      } else if (tier === "worker") {
        workers.push(row);
      } else {
        unknown.push(row);
      }
    }
    const byQueenSwarm = new Set(
      swarms.map((s) => s.queen_agent_id).filter((x): x is string => Boolean(x)),
    );
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
    for (const m of [...managers, ...inferredManagers]) {
      if (queenId && m.id === queenId) {
        continue;
      }
      if (!seen.has(m.id)) {
        seen.add(m.id);
        managerList.push(m);
      }
    }
    const pool = [...workers, ...unknown];
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
      if (!assigned) {
        ungrouped.push(w);
      }
    }
    return { queen, managers: managerList, teamByManager, ungrouped };
  }, [agents, swarms]);

  if (loading) {
    return (
      <div className="py-16 text-center font-mono text-sm text-[var(--qs-text-3)]">Načítavam hierarchiu…</div>
    );
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Hierarchia úľa"
        subtitle="Queen riadi manažérov · každý manažér má vlastný tím robotníkov."
      />

      <div className="flex flex-col items-center pb-10">
        {tree.queen ? (
          <>
            <HexAgentCard agent={tree.queen} href={`/agents/${tree.queen.id}`} isQueen tilePx={150} />
            {(tree.managers.length > 0 || tree.ungrouped.length > 0) && (
              <VerticalRule color="rgba(255,184,0,0.45)" h={36} />
            )}
          </>
        ) : (
          <p className="text-center font-mono text-sm text-[var(--qs-text-3)]">
            Žiadny orchestrátor v dátach — spawn „Queen“ cez Agents.
          </p>
        )}

        {tree.managers.length > 0 ? (
          <div className="relative flex w-full max-w-[1100px] flex-col items-center">
            {tree.managers.length > 1 ? (
              <div
                className="pointer-events-none absolute left-1/2 top-0 z-0 h-0.5 -translate-x-1/2 rounded-full bg-[#FFB80033]"
                style={{ width: `${(tree.managers.length - 1) * (130 + 18)}px` }}
                aria-hidden
              />
            ) : null}
            <div className="relative z-[1] flex flex-wrap justify-center gap-5">
              {tree.managers.map((mgr) => {
                const mgrSwarm =
                  swarms.find((s) => s.queen_agent_id === mgr.id) ??
                  (mgr.swarm_id ? swarms.find((s) => s.id === mgr.swarm_id) : undefined);
                const accent = mgrSwarm ? displaySwarmColor(mgrSwarm) : "#FFB800";
                const team = tree.teamByManager.get(mgr.id) ?? [];
                return (
                  <div key={mgr.id} className="flex flex-col items-center gap-0">
                    <HexAgentCard agent={mgr} href={`/agents/${mgr.id}`} tilePx={130} />
                    {team.length > 0 ? (
                      <>
                        <VerticalRule color={accent} h={28} />
                        {team.length > 1 ? (
                          <div
                            className="mb-1 h-0.5 rounded-full"
                            style={{
                              width: `${(Math.min(team.length, 4) - 1) * (100 + 10)}px`,
                              backgroundColor: `${accent}33`,
                            }}
                            aria-hidden
                          />
                        ) : null}
                        <div className="flex flex-col items-center gap-2">
                          {Array.from({ length: Math.ceil(team.length / 4) }, (_, rowIdx) =>
                            team.slice(rowIdx * 4, rowIdx * 4 + 4),
                          ).map((row, rowIdx) => (
                            <div key={rowIdx} className="flex flex-wrap justify-center gap-2.5">
                              {row.map((w) => (
                                <HexAgentCard key={w.id} agent={w} href={`/agents/${w.id}`} tilePx={100} />
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
          <div className="mt-10 w-full max-w-[1100px]">
            <p className="mb-4 text-center font-mono text-[10px] uppercase tracking-[0.12em] text-[var(--qs-text-3)]">
              Robotníci mimo tímov ({tree.ungrouped.length})
            </p>
            <div className="qs-hex-grid justify-center">
              {tree.ungrouped.map((w) => (
                <HexAgentCard key={w.id} agent={w} href={`/agents/${w.id}`} tilePx={100} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
