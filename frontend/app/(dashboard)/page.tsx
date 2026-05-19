import { ColonyConsole } from "@/components/hive/colony-console";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { AgentRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function HiveHomeDashboard() {
  const agents = await hiveServerRawJson<AgentRow[]>("/agents?limit=200");

  return (
    <div className="pb-8">
      <ColonyConsole initialAgents={agents ?? []} rosterSyncPending={agents === null} />
    </div>
  );
}
