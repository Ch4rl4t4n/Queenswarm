import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const TradingJournalPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/trading-journal-page-client").then((mod) => ({
      default: mod.TradingJournalPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function TradingJournalModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <TradingJournalPageClient />
    </Suspense>
  );
}
