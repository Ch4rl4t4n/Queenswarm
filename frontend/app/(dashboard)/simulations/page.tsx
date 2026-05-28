import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { SimulationRow } from "@/lib/hive-types";

const SimulationsPageClient = nextDynamic(
  () => import("@/components/hive/simulations-page-client").then((mod) => ({ default: mod.SimulationsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default async function SimulationsPage(): Promise<JSX.Element> {
  if (!SIMULATIONS_ENABLED) {
    return <SimulationsPageClient audits={null} disabled />;
  }

  const audits = await hiveServerRawJson<SimulationRow[]>("/simulations?limit=50");

  return <SimulationsPageClient audits={audits} />;
}
