import { redirect } from "next/navigation";

import { OutputsInteractivePanel } from "@/components/hive/outputs-interactive-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

/** My Outputs — Postgres + disk + Chroma archive for completed missions (Phase 0.51). */
export default async function OutputsPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/knowledge#outputs");
  }

  const rows = await hiveServerRawJson<FinalDeliverableSummaryRow[]>("/outputs?limit=80");

  if (!rows) {
    return (
      <p className="font-(family-name:--font-poppins) text-sm text-danger">
        Outputs archive unreachable — authenticate the cockpit or check API health.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="My Outputs"
        subtitle="Archived Markdown + structured JSON · semantic search · versioned Ballroom lineages · PDF export deliberately off (501)."
      />
      <OutputsInteractivePanel initialItems={rows} />
    </div>
  );
}
