"use client";

import confetti from "canvas-confetti";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef } from "react";

import { HexCard, type GlowColor } from "@/components/ui/HexCard";
import { LoadingHex } from "@/components/ui/LoadingHex";
import { PollenBar } from "@/components/ui/PollenBar";
import { StatusDot } from "@/components/ui/StatusDot";
import { useAgents } from "@/lib/hooks/use-agents";
import { useTasks } from "@/lib/hooks/use-tasks";
import type { AgentRow } from "@/lib/hive-types";

const REFRESH_MS = 5000;

const swarmEmoji: Record<string, string> = {
  unassigned: "⬢",
  scout: "🔍",
  eval: "🧠",
  sim: "🎲",
  action: "⚡",
};

const swarmGlow: Record<string, GlowColor> = {
  unassigned: "cyan",
  scout: "cyan",
  eval: "green",
  sim: "amber",
  action: "magenta",
};

function inferSwarmKey(agent: AgentRow): keyof typeof swarmEmoji {
  const sid = agent.swarm_id;
  const anchored = sid !== undefined && sid !== null && String(sid).trim().length > 0;
  if (!anchored) {
    return "unassigned";
  }
  const raw = (agent.swarm_purpose ?? "").toLowerCase();
  if (raw === "scout") {
    return "scout";
  }
  if (raw === "eval") {
    return "eval";
  }
  if (raw === "simulation") {
    return "sim";
  }
  if (raw === "action") {
    return "action";
  }
  const label = (agent.swarm_name ?? "").toLowerCase();
  if (label.includes("scout")) {
    return "scout";
  }
  if (label.includes("eval")) {
    return "eval";
  }
  if (label.includes("sim")) {
    return "sim";
  }
  if (label.includes("action")) {
    return "action";
  }
  return "unassigned";
}

function mapHiveStatus(raw: string): "active" | "idle" | "error" | "paused" {
  const u = raw.toUpperCase();
  if (u === "RUNNING" || u === "ACTIVE" || u === "BUSY") {
    return "active";
  }
  if (u === "PAUSED") {
    return "paused";
  }
  if (u === "ERROR" || u === "OFFLINE") {
    return "error";
  }
  return "idle";
}

interface DashboardBeeHexGridProps {
  rosterTarget: number;
}

/** Phase G2 — polled bee lattice with canvas-confetti when completed tasks increase. */
export function DashboardBeeHexGrid({ rosterTarget }: DashboardBeeHexGridProps) {
  const router = useRouter();
  const { agents: agentsData, isLoading: isLoadingAgents } = useAgents(REFRESH_MS);
  const { tasks: tasksData } = useTasks("limit=200&status=completed", REFRESH_MS);

  const agents: AgentRow[] = useMemo(() => agentsData ?? [], [agentsData]);

  const completedCount = tasksData?.length ?? 0;

  const prevCompletedRef = useRef<number | null>(null);

  useEffect(() => {
    if (prevCompletedRef.current === null) {
      prevCompletedRef.current = completedCount;
      return;
    }
    if (completedCount > prevCompletedRef.current) {
      void confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#FFB800", "#00FFFF", "#FF00AA", "#00FF88"],
      });
    }
    prevCompletedRef.current = completedCount;
  }, [completedCount]);

  const targetDisplay = rosterTarget > 0 ? rosterTarget : 29;

  return (
    <section className="mt-8 rounded-[22px] border border-[#1a1a3e]/80 bg-[#0d0d2b]/40 p-6 neon-border-pg">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2
          className="text-[#FFB800] font-semibold text-lg font-[family-name:var(--font-poppins)]"
        >
          🐝 Active Bees
          <span className="ml-2 font-normal font-[family-name:var(--font-jetbrains-mono)] text-sm text-gray-400">
            {agents.length} / {targetDisplay}
          </span>
        </h2>
      </div>
      {isLoadingAgents ? (
        <LoadingHex size={64} />
      ) : agents.length === 0 ? (
        <div className="py-12 text-center text-gray-500">
          <div className="mb-3 text-4xl">🐝</div>
          <p className="text-sm">No bees yet — run seed script to create your swarm</p>
        </div>
      ) : (
        <div className="flex flex-wrap gap-3">
          {[...agents]
            .sort((a, b) => {
              const ka = inferSwarmKey(a);
              const kb = inferSwarmKey(b);
              if (ka !== kb) {
                return ka.localeCompare(kb);
              }
              return (b.pollen_points ?? 0) - (a.pollen_points ?? 0);
            })
            .map((agent: AgentRow) => {
              const key = inferSwarmKey(agent);
              const glow = swarmGlow[key] ?? "cyan";
              const dot = mapHiveStatus(agent.status ?? "idle");

              return (
                <HexCard
                  key={agent.id}
                  glowColor={glow}
                  size="md"
                  onClick={() => router.push(`/agents/${agent.id}`)}
                >
                  <div className="flex flex-col items-center gap-1.5 px-3 text-center">
                    <span className="text-xl leading-none">{swarmEmoji[key] ?? "🐝"}</span>
                    <span className="max-w-[100px] truncate font-[family-name:var(--font-jetbrains-mono)] text-[10px] leading-tight text-white">
                      {agent.name}
                    </span>
                    <StatusDot status={dot} size="sm" />
                    <div className="w-16">
                      <PollenBar value={agent.pollen_points ?? 0} max={1000} showLabel={false} />
                    </div>
                  </div>
                </HexCard>
              );
            })}
        </div>
      )}
    </section>
  );
}
