import nextDynamic from "next/dynamic";

import { LegacyRouteRedirect } from "@/components/hive/legacy-route-redirect";
import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

const HiveMindExplorer = nextDynamic(async () => {
  const mod = await import("@/components/hive/hive-mind-explorer");
  return { default: mod.HiveMindExplorer };
});

/** HiveMind / shared memory explorer (Neo4j + Chroma lane + Markdown vault mirrors). */
export default function HiveMindPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    return <LegacyRouteRedirect target="/knowledge#hivemind" label="Redirecting to Knowledge…" />;
  }
  return <HiveMindExplorer />;
}
