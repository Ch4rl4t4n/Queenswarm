import nextDynamic from "next/dynamic";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";
import { V4PageCanvas } from "@/components/ui/v4";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { SimulationRow } from "@/lib/hive-types";

const SimulationsPageClient = nextDynamic(
  () => import("@/components/hive/simulations-page-client").then((mod) => ({ default: mod.SimulationsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

const HEADER_SUBTITLE =
  "Only payloads that survived dockerized guardrails bubble up to ballroom operators — ignite confetti whenever a new sandbox goes green.";

export default async function SimulationsPage() {
  if (!SIMULATIONS_ENABLED) {
    return (
      <V4PageCanvas className="gap-6">
        <HivePageHeader title="Verified simulation vault" subtitle={HEADER_SUBTITLE} />
        <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
          <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
            Simulations module is disabled. Enable <code>NEXT_PUBLIC_SIMULATIONS_ENABLED=true</code> for this section.
          </p>
        </div>
      </V4PageCanvas>
    );
  }

  const audits = await hiveServerRawJson<SimulationRow[]>("/simulations?limit=50");

  return <SimulationsPageClient audits={audits} />;
}
