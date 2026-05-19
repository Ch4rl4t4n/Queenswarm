"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import useSWR from "swr";

import { AgentsPageRoster } from "@/components/hive/agents-page-roster";
import { AgentsSessionsPanel } from "@/components/hive/agents-sessions-panel";
import { BeeRoleTypesSection } from "@/components/hive/bee-role-types-section";
import { HierarchyPageConsole } from "@/components/hive/hierarchy-page-console";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4Card, V4CardHeader, V4PageCanvas } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsPageClientProps {
  initialAgents: AgentRow[];
  /** SSR roster fetch failed — client SWR will retry. */
  rosterSyncPending?: boolean;
}

export function AgentsPageClient({ initialAgents, rosterSyncPending = false }: AgentsPageClientProps) {
  const { data: agents = initialAgents } = useSWR<AgentRow[]>(
    "hive/agents-page",
    () => hiveGet<AgentRow[]>("agents?limit=120"),
    { fallbackData: initialAgents, refreshInterval: COCKPIT_POLL_BOARD_MS },
  );

  const { data: swarms } = useSWR<{ id: string }[]>(
    "hive/agents-page-swarms",
    async () => {
      const rows = await hiveGet<{ id: string; is_active?: boolean; name?: string }[]>("swarms?limit=120");
      return rows.filter((s) => s.is_active !== false && !String(s.name ?? "").includes("__inactive_"));
    },
    { refreshInterval: COCKPIT_POLL_BOARD_MS },
  );

  const swarmCount = swarms?.length ?? 0;

  return (
    <V4PageCanvas>
      {rosterSyncPending ? (
        <p className="rounded-xl border border-alert/30 bg-alert/10 px-4 py-3 text-sm text-(--qs-text-2) lg:hidden">
          Agent ledger syncing — live poll will retry shortly.
        </p>
      ) : null}
      <HivePageHeader
        title="Agents"
        subtitle="Unified control plane for supervisor sessions, active bees, and hierarchy topology."
        actions={
          <div className="v4-page-header-actions-group flex flex-wrap items-center gap-2">
            <span className="w-full text-xs tabular-nums text-(--qs-text-3) sm:w-auto">
              {agents.length} bees · {swarmCount} swarms
            </span>
            <Link href="/agents/new" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Plus className="h-4 w-4" aria-hidden />
              Templates
            </Link>
            <Link href="/agents/new" className="qs-btn qs-btn--primary qs-btn--sm gap-2">
              <Plus className="h-4 w-4" aria-hidden />
              Spawn agent
            </Link>
          </div>
        }
      />

      <BeeRoleTypesSection agents={agents} />

      <AgentsSessionsPanel variant="v4" />

      <AgentsPageRoster initialAgents={agents} variant="v4" />

      <V4Card id="hierarchy">
        <V4CardHeader
          title="Hierarchy graph"
          description="Queen → managers → workers topology with grouped swarm lanes."
          actions={
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => window.location.reload()}>
              Re-layout
            </button>
          }
        />
        <HierarchyPageConsole showHeader={false} />
      </V4Card>
    </V4PageCanvas>
  );
}
