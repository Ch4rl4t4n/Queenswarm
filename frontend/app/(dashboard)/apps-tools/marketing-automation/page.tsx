import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const MarketingAutomationPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/marketing-automation-page-client").then((mod) => ({
      default: mod.MarketingAutomationPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function MarketingAutomationModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <MarketingAutomationPageClient />
    </Suspense>
  );
}
