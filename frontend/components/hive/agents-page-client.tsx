"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import useSWR from "swr";

import { AgentsContextGraphStrip } from "@/components/hive/agents-context-graph-strip";
import { AgentsLearningLoopPanel } from "@/components/hive/agents-learning-loop-panel";
import { AgentsPageSyncBanner } from "@/components/hive/agents-page-sync-banner";
import { AgentsPageRoster } from "@/components/hive/agents-page-roster";
import { AgentsRuntimeStatusStrip } from "@/components/hive/agents-runtime-status-strip";
import { AgentsSessionsPanel } from "@/components/hive/agents-sessions-panel";
import { BeeRoleTypesSection } from "@/components/hive/bee-role-types-section";
import { HierarchyGraphCollapsible } from "@/components/hive/hierarchy-graph-collapsible";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";
import { V4PageCanvas } from "@/components/ui/v4";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { hiveGet } from "@/lib/api";
import { formatAgentsFetchError } from "@/lib/agents-page-status";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import { useRouteHashScroll } from "@/lib/hooks/use-route-hash-scroll";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsPageClientProps {
  initialAgents: AgentRow[];
  /** SSR roster fetch failed — client SWR will retry. */
  rosterSyncPending?: boolean;
}

export function AgentsPageClient({ initialAgents, rosterSyncPending = false }: AgentsPageClientProps) {
  useRouteHashScroll();

  const pollOptions = useRouteScopedPollOptions(COCKPIT_POLL_BOARD_MS, "/agents");
  const {
    data: agents = initialAgents,
    error: agentsError,
    isValidating: agentsValidating,
    mutate: mutateAgents,
  } = useSWR<AgentRow[]>(
    "hive/agents-page",
    () => hiveGet<AgentRow[]>(`agents?limit=${COCKPIT_PERF.fullAgentsLimit}`),
    { fallbackData: initialAgents, ...pollOptions },
  );
  const rosterAgents = Array.isArray(agents) ? agents : initialAgents;

  const {
    data: swarms,
    error: swarmsError,
    mutate: mutateSwarms,
  } = useSWR<{ id: string }[]>(
    "hive/agents-page-swarms",
    async () => {
      const rows = await hiveGet<{ id: string; is_active?: boolean; name?: string }[]>("swarms?limit=120");
      return rows.filter((s) => s.is_active !== false && !String(s.name ?? "").includes("__inactive_"));
    },
    pollOptions,
  );

  const swarmCount = swarms?.length ?? 0;
  const rosterError = formatAgentsFetchError(agentsError);
  const swarmLoadError = formatAgentsFetchError(swarmsError);

  async function retryAgentsSync(): Promise<void> {
    await Promise.all([mutateAgents(), mutateSwarms()]);
  }

  return (
    <V4PageCanvas>
      <AgentsPageSyncBanner
        rosterSyncPending={rosterSyncPending && !rosterError}
        rosterError={rosterError}
        swarmsError={swarmLoadError}
        onRetry={rosterError || swarmLoadError || rosterSyncPending ? () => void retryAgentsSync() : undefined}
        retryBusy={agentsValidating}
      />
      <HivePageHeader
        className="mb-3 lg:mb-6"
        title="Agents"
        subtitle="Unified control plane for supervisor sessions, active bees, and hierarchy topology."
        status={
          <Link href="/agents/new" className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-2">
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            Spawn agent
          </Link>
        }
        actions={
          <span className="qs-page-header-stats text-xs tabular-nums text-(--qs-text-3)">
            {rosterAgents.length} bees · {swarmCount} swarms
          </span>
        }
      />

      <HubEcosystemStrip preset="agents" />

      <BeeRoleTypesSection agents={rosterAgents} />

      <AgentsRuntimeStatusStrip />

      <AgentsContextGraphStrip />

      <AgentsLearningLoopPanel />

      <AgentsSessionsPanel variant="v4" />

      <AgentsPageRoster agents={rosterAgents} variant="v4" />

      <HierarchyGraphCollapsible beeCount={rosterAgents.length} />
    </V4PageCanvas>
  );
}
