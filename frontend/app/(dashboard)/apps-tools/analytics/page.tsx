import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const AnalyticsWorkspacePageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/analytics-workspace-page-client").then((mod) => ({
      default: mod.AnalyticsWorkspacePageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function AnalyticsWorkspaceModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <AnalyticsWorkspacePageClient />
    </Suspense>
  );
}
