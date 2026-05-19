import nextDynamic from "next/dynamic";
import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";
import { integrationsTabHref } from "@/lib/integrations-routes";

export const dynamic = "force-dynamic";

const ConnectorsConsole = nextDynamic(async () => {
  const mod = await import("@/components/connectors/connectors-console");
  return { default: mod.ConnectorsConsole };
});

/** PostgreSQL MCP manifest cockpit + Phase 3 Communication & Knowledge templates (Phase 1.2 → 3). */
export default function ConnectorsPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect(integrationsTabHref("hub"));
  }
  return <ConnectorsConsole />;
}
