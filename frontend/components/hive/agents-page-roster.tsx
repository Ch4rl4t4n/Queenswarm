"use client";

import type { JSX } from "react";

import { useRouter } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { AgentsLiveSection } from "@/components/hive/agents-live-section";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsPageRosterProps {
  initialAgents: AgentRow[];
}

export function AgentsPageRoster({ initialAgents }: AgentsPageRosterProps): JSX.Element {
  const router = useRouter();
  const [rebalanceBusy, setRebalanceBusy] = useState(false);

  const { data = initialAgents } = useSWR<AgentRow[]>(
    "hive/agents-page-roster",
    () => hiveGet<AgentRow[]>("agents?limit=120"),
    { fallbackData: initialAgents, refreshInterval: 8000 },
  );

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
      agents={data}
      onAgentActivate={goAgent}
      onRebalanceHive={rebalanceHive}
      rebalanceBusy={rebalanceBusy}
      spawnAgentHref="/agents/new"
    />
  );
}
