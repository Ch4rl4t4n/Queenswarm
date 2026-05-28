import { redirect } from "next/navigation";

import { cockpitDynamic } from "@/lib/cockpit-dynamic-imports";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import type { DashboardCockpitBundle } from "@/lib/cockpit-bundle";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";

const ColonyConsole = cockpitDynamic(() =>
  import("@/components/hive/colony-console").then((mod) => ({ default: mod.ColonyConsole })),
);

export const dynamic = "force-dynamic";

/** Legacy Queen dashboard — redirects to Cockpit when Operator Control Plane is enabled. */
export default async function HiveAdvancedDashboardPage() {
  if (OPERATOR_CONTROL_PLANE_ENABLED) {
    redirect("/agentic-os");
  }

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
