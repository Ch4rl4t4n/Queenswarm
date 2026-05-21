import nextDynamic from "next/dynamic";

import { ColonyConsoleSkeleton } from "@/components/hive/colony-console-skeleton";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import type { DashboardCockpitBundle } from "@/lib/cockpit-bundle";
import { hiveServerRawJson } from "@/lib/hive-server";

const ColonyConsole = nextDynamic(
  () => import("@/components/hive/colony-console").then((mod) => ({ default: mod.ColonyConsole })),
  { loading: () => <ColonyConsoleSkeleton /> },
);

export const dynamic = "force-dynamic";

export default async function HiveHomeDashboard() {
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
