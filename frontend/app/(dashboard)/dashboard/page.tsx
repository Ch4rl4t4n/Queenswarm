import { cockpitDynamic } from "@/lib/cockpit-dynamic-imports";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import type { DashboardCockpitBundle } from "@/lib/cockpit-bundle";
import { hiveServerRawJson } from "@/lib/hive-server";

const ColonyConsole = cockpitDynamic(() =>
  import("@/components/hive/colony-console").then((mod) => ({ default: mod.ColonyConsole })),
);

export const dynamic = "force-dynamic";

/** Legacy Queen dashboard — linked from Cockpit as Advanced. */
export default async function HiveAdvancedDashboardPage() {
  const cockpit = await hiveServerRawJson<DashboardCockpitBundle>(
    `/dashboard/cockpit?agents_limit=${COCKPIT_PERF.dashboardAgentsLimit}&tasks_limit=${COCKPIT_PERF.recentTasksLimit}`,
  );

  return (
    <ColonyConsole
      initialCockpit={cockpit}
      initialAgents={cockpit?.agents ?? []}
      rosterSyncPending={cockpit === null}
    />
  );
}
