import { cockpitDynamic } from "@/lib/cockpit-dynamic-imports";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

const AgentsPageClient = cockpitDynamic(() =>
  import("@/components/hive/agents-page-client").then((mod) => ({ default: mod.AgentsPageClient })),
);

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>(`/agents?limit=${COCKPIT_PERF.fullAgentsLimit}`);

  return <AgentsPageClient initialAgents={rows ?? []} rosterSyncPending={rows === null} />;
}
