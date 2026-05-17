import nextDynamic from "next/dynamic";
import { redirect } from "next/navigation";

import { PHASE70_CONSOLIDATED_NAV_ENABLED } from "@/lib/feature-flags";

export const dynamic = "force-dynamic";

const HiveMindExplorer = nextDynamic(async () => {
  const mod = await import("@/components/hive/hive-mind-explorer");
  return { default: mod.HiveMindExplorer };
});

/** HiveMind / shared memory explorer (Neo4j + Chroma lane + Markdown vault mirrors). */
export default function HiveMindPage() {
  if (PHASE70_CONSOLIDATED_NAV_ENABLED) {
    redirect("/knowledge#hivemind");
  }
  return <HiveMindExplorer />;
}
