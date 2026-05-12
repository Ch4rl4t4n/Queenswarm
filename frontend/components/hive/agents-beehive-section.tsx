"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { AgentRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";
import { AgentHexCard } from "@/components/hive/agent-hex-card";
import { NeonButton } from "@/components/ui/neon-button";

type AgentFilterTab = "all" | "busy" | "simulate";

interface AgentsBeehiveSectionProps {
  agents: AgentRow[];
}

/** Agents grid + pill filters aligned with cockpit mock toolbar. */
export function AgentsBeehiveSection({ agents }: AgentsBeehiveSectionProps) {
  const [tab, setTab] = useState<AgentFilterTab>("all");

  const rows = useMemo(() => {
    if (tab === "all") {
      return agents;
    }
    if (tab === "busy") {
      return agents.filter((a) =>
        ["RUNNING", "BUSY", "EXECUTING"].includes(a.status.toUpperCase()),
      );
    }
    return agents.filter((a) => a.role.toUpperCase().includes("SIM"));
  }, [agents, tab]);

  function tabClass(active: boolean): string {
    return cn(
      "shrink-0 whitespace-nowrap rounded-full px-4 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold uppercase tracking-[0.12em]",
      active
        ? "bg-pollen text-black shadow-[0_0_18px_rgb(255_184_0/0.35)]"
        : "border border-cyan/[0.15] text-zinc-400 hover:border-pollen/30 hover:text-pollen",
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-3 overflow-x-auto border-b border-cyan/[0.1] pb-4 hive-scrollbar sm:flex-wrap sm:gap-6">
        {(
          [
            ["all", "All scouts"],
            ["busy", "Busy"],
            ["simulate", "Simulate lane"],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" className={tabClass(tab === id)} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div />
        <div className="flex flex-wrap gap-2">
          <NeonButton variant="ghost" asChild className="text-xs uppercase">
            <Link href="/simulations">Open simulation</Link>
          </NeonButton>
          <NeonButton variant="primary" asChild className="text-xs uppercase">
            <Link href="/agents">+ Invite agent</Link>
          </NeonButton>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-5">
        {rows.map((agent) => (
          <AgentHexCard key={agent.id} agent={agent} />
        ))}
      </div>
      {rows.length === 0 ? (
        <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-zinc-500">No bees in this shard.</p>
      ) : null}
    </div>
  );
}
