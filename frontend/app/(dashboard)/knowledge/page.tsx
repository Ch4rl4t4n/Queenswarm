import { KnowledgePageClient } from "@/components/hive/knowledge-page-client";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function KnowledgePage() {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("knowledge"));
  }

  const outputs = await hiveServerRawJson<FinalDeliverableSummaryRow[]>("/outputs?limit=80");

  return <KnowledgePageClient initialOutputs={outputs ?? []} archiveSyncPending={outputs === null} />;
}
