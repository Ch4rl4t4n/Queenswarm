import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const MarketingTeamPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/marketing-team-page-client").then((mod) => ({
      default: mod.MarketingTeamPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function MarketingTeamModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <MarketingTeamPageClient />
    </Suspense>
  );
}
