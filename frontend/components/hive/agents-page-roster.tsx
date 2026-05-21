"use client";

import type { JSX } from "react";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AgentsLiveSection } from "@/components/hive/agents-live-section";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsPageRosterProps {
  agents: AgentRow[];
  variant?: "default" | "v4";
}

/** Live roster board — data comes from the parent page SWR (single poll). */
export function AgentsPageRoster({ agents, variant = "default" }: AgentsPageRosterProps): JSX.Element {
  const router = useRouter();
  const [rebalanceBusy, setRebalanceBusy] = useState(false);

  function goAgent(agent: AgentRow): void {
    const target = agent.has_universal_config ? `/agents/${agent.id}` : `/agents/${agent.id}/edit`;
    router.push(target);
  }

  async function rebalanceHive(): Promise<void> {
    setRebalanceBusy(true);
    try {
      const res = await hivePostJson<{ message?: string }>("agents/wake-all", {});
      toast.success(res.message ?? "Agents nudged to idle.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Rebalance failed";
      toast.error(msg);
    } finally {
      setRebalanceBusy(false);
    }
  }

  return (
    <AgentsLiveSection
      agents={agents}
      onAgentActivate={goAgent}
      onRebalanceHive={rebalanceHive}
      rebalanceBusy={rebalanceBusy}
      spawnAgentHref="/agents/new"
      virtualizeList
      title={variant === "v4" ? "Active agents" : "Agents"}
      description={
        variant === "v4"
          ? "Live roster, health/status, and direct actions for each bee in one scanable board."
          : undefined
      }
    />
  );
}
