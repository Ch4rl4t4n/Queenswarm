import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const ResearchWorkspacePageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/research-workspace-page-client").then((mod) => ({
      default: mod.ResearchWorkspacePageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function ResearchWorkspaceModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <ResearchWorkspacePageClient />
    </Suspense>
  );
}
