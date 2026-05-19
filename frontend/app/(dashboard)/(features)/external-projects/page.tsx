import nextDynamic from "next/dynamic";
import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { integrationsTabHref } from "@/lib/integrations-routes";

export const dynamic = "force-dynamic";

const ExternalProjectsConsole = nextDynamic(async () => {
  const mod = await import("@/components/external-projects/external-projects-console");
  return { default: mod.ExternalProjectsConsole };
});

/** Phase 2.5 — Universal External Project Integration cockpit (MCP + REST + WS). */
export default function ExternalProjectsPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(integrationsTabHref("external"));
  }
  return <ExternalProjectsConsole />;
}
