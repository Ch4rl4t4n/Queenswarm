import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const EcommerceAutomationPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/ecommerce-automation-page-client").then((mod) => ({
      default: mod.EcommerceAutomationPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function EcommerceAutomationModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <EcommerceAutomationPageClient />
    </Suspense>
  );
}
