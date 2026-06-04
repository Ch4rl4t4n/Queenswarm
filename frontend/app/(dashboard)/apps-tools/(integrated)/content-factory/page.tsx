import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const ContentFactoryPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/content-factory-page-client").then((mod) => ({
      default: mod.ContentFactoryPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function ContentFactoryModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <ContentFactoryPageClient />
    </Suspense>
  );
}
