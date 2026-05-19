import { AgentsPageClient } from "@/components/hive/agents-page-client";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const rows = await hiveServerRawJson<AgentRow[]>("/agents?limit=120");

  return <AgentsPageClient initialAgents={rows ?? []} rosterSyncPending={rows === null} />;
}
