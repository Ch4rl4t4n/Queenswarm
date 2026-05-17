import { redirect } from "next/navigation";

import { HivePageHeader } from "@/components/hive/hive-page-header";
import { KnowledgePageConsole } from "@/components/hive/knowledge-page-console";
import { PHASE70_CONSOLIDATED_NAV_ENABLED, RECIPES_ENABLED } from "@/lib/feature-flags";
import { hubFallbackTarget } from "@/lib/hive-navigation-mode";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { FinalDeliverableSummaryRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function KnowledgePage(): Promise<JSX.Element> {
  if (!PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(hubFallbackTarget("knowledge"));
  }

  const outputs = await hiveServerRawJson<FinalDeliverableSummaryRow[]>("/outputs?limit=80");
  if (!outputs) {
    return (
      <p className="font-(family-name:--font-poppins) text-sm text-danger">
        Knowledge archive unavailable - authenticate the cockpit or verify API health.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Knowledge"
        subtitle="One knowledge plane: HiveMind retrieval context, outputs archive actions, and learning recipes loops."
        info={{
          title: "Knowledge",
          description: "Pamäťový priestor pre retrieval, outputs archív a learning loops.",
          options: ["HiveMind kontext", "Outputs audit", "Recipes/Learning reuse"],
        }}
      />
      <KnowledgePageConsole initialOutputs={outputs} recipesEnabled={RECIPES_ENABLED} />
    </div>
  );
}
