import { redirect } from "next/navigation";

import { cockpitDynamic } from "@/lib/cockpit-dynamic-imports";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";

const KnowledgePageClient = cockpitDynamic(() =>
  import("@/components/hive/knowledge-page-client").then((mod) => ({ default: mod.KnowledgePageClient })),
);

export const dynamic = "force-dynamic";

export default async function KnowledgePage() {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("knowledge"));
  }

  const outputs = await hiveServerRawJson<FinalDeliverableSummaryRow[]>("/outputs?limit=80");

  return <KnowledgePageClient initialOutputs={outputs ?? []} archiveSyncPending={outputs === null} />;
}
