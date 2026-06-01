"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { AgentsContextGraphStrip } from "@/components/hive/agents-context-graph-strip";
import { AgentsLearningLoopPanel } from "@/components/hive/agents-learning-loop-panel";
import { AgentsPageRoster } from "@/components/hive/agents-page-roster";
import { AgentsRuntimeStatusStrip } from "@/components/hive/agents-runtime-status-strip";
import { AgentsSessionsPanel } from "@/components/hive/agents-sessions-panel";
import { FirstRunWizardPanel } from "@/components/hive/first-run-wizard-panel";
import { BeeRoleTypesSection } from "@/components/hive/bee-role-types-section";
import { HierarchyGraphCollapsible } from "@/components/hive/hierarchy-graph-collapsible";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";
import { usePlatform } from "@/components/hive/platform-context";
import { hiveGet } from "@/lib/api";
import { hivePageShellAgentsSync } from "@/lib/hive-page-error";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { formatAgentsFetchError } from "@/lib/agents-page-status";
import {
  AGENTS_ECOSYSTEM_SECTIONS,
  agentsEcosystemSectionFromHash,
  agentsEcosystemSectionHref,
  resolveAgentsEcosystemSection,
  type AgentsEcosystemSection,
} from "@/lib/agents-ecosystem-routes";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { EXECUTION_LANE_CROSS_LINK_LABELS, FORAGERS_PATH } from "@/lib/execution-lane-routes";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsPageClientProps {
  initialAgents: AgentRow[];
  /** SSR roster fetch failed — client SWR will retry. */
  rosterSyncPending?: boolean;
}

const SECTION_IDS = AGENTS_ECOSYSTEM_SECTIONS.map((row) => row.id);

function readEcosystemSectionFromLocation(): AgentsEcosystemSection {
  if (typeof window === "undefined") {
    return SECTION_IDS[0] ?? "roles";
  }
  return resolveAgentsEcosystemSection({ hash: window.location.hash });
}

export function AgentsPageClient({ initialAgents, rosterSyncPending = false }: AgentsPageClientProps) {
  const { soloMode } = usePlatform();
  const [section, setSection] = useState<AgentsEcosystemSection>(readEcosystemSectionFromLocation);

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

  const selectSection = useCallback((next: AgentsEcosystemSection) => {
    setSection(next);
    window.history.replaceState(null, "", agentsEcosystemSectionHref(next));
  }, []);

  useEffect(() => {
    const syncFromHash = (): void => {
      const fromHash = agentsEcosystemSectionFromHash(window.location.hash);
      if (fromHash) {
        setSection(fromHash);
        return;
      }
      const next = resolveAgentsEcosystemSection({});
      setSection(next);
      window.history.replaceState(null, "", agentsEcosystemSectionHref(next));
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  const retryAgentsSync = useCallback(async (): Promise<void> => {
    await Promise.all([mutateAgents(), mutateSwarms()]);
  }, [mutateAgents, mutateSwarms]);

  const shellSyncAlert = useMemo(
    () =>
      hivePageShellAgentsSync({
        rosterError,
        swarmsError: swarmLoadError,
        rosterSyncPending: rosterSyncPending && !rosterError,
        onRetry:
          rosterError || swarmLoadError || rosterSyncPending ? retryAgentsSync : undefined,
        retryBusy: agentsValidating,
      }),
    [rosterError, swarmLoadError, rosterSyncPending, agentsValidating, retryAgentsSync],
  );

  return (
    <HivePageShell
      className="mb-3 lg:mb-6"
      title="Agents"
      subtitle="Unified control plane for supervisor sessions, active bees, and hierarchy topology."
      hintKey="agents"
      error={shellSyncAlert}
      status={
        soloMode ? (
          <Link href="/agents/new" className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 gap-2">
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            Add agent bee
          </Link>
        ) : (
          <Link href="/agents/new" className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-2">
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            Spawn agent
          </Link>
        )
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={FORAGERS_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {EXECUTION_LANE_CROSS_LINK_LABELS.toForagers}
          </Link>
          <span className="qs-page-header-stats text-xs tabular-nums text-(--qs-text-3)">
            {rosterAgents.length} bees · {swarmCount} swarms
          </span>
        </div>
      }
      subnav={
        <>
          <HubEcosystemStrip preset="agents" />
          <HiveSubnavRow
            items={AGENTS_ECOSYSTEM_SECTIONS}
            activeId={section}
            onChange={(id) => selectSection(id as AgentsEcosystemSection)}
            ariaLabel="Agents ecosystem sections"
            menuKey="agents-ecosystem"
          />
        </>
      }
    >
      <HiveSubnavContent className="space-y-6">
        {section === "sessions" ? <FirstRunWizardPanel /> : null}
        {section === "roles" ? <BeeRoleTypesSection agents={rosterAgents} /> : null}
        {section === "runtime" ? <AgentsRuntimeStatusStrip /> : null}
        {section === "context" ? <AgentsContextGraphStrip expanded /> : null}
        {section === "learning" ? <AgentsLearningLoopPanel /> : null}
        {section === "sessions" ? <AgentsSessionsPanel variant="v4" /> : null}
        {section === "roster" ? <AgentsPageRoster agents={rosterAgents} variant="v4" /> : null}
        {section === "hierarchy" ? <HierarchyGraphCollapsible beeCount={rosterAgents.length} expanded /> : null}
      </HiveSubnavContent>
    </HivePageShell>
  );
}
