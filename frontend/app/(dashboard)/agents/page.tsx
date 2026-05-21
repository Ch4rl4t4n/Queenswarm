import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

const AgentsPageClient = nextDynamic(
  () => import("@/components/hive/agents-page-client").then((mod) => ({ default: mod.AgentsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>(`/agents?limit=${COCKPIT_PERF.fullAgentsLimit}`);

  return <AgentsPageClient initialAgents={rows ?? []} rosterSyncPending={rows === null} />;
}
