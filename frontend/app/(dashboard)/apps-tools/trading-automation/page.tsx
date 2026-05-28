import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const TradingAutomationPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/trading-automation-page-client").then((mod) => ({
      default: mod.TradingAutomationPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function TradingAutomationModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <TradingAutomationPageClient />
    </Suspense>
  );
}
