import nextDynamic from "next/dynamic";

import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";
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
    return <LegacyRouteRedirect target={integrationsTabHref("external")} label="Redirecting to Integrations…" />;
  }
  return <ExternalProjectsConsole />;
}
