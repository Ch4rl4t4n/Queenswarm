import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const McpOpsStudioPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/mcp-ops-studio-page-client").then((mod) => ({
      default: mod.McpOpsStudioPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function McpOpsStudioModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <McpOpsStudioPageClient />
    </Suspense>
  );
}
