import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const BrowserAutomationPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/browser-automation-page-client").then((mod) => ({
      default: mod.BrowserAutomationPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function BrowserAutomationModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <BrowserAutomationPageClient />
    </Suspense>
  );
}
