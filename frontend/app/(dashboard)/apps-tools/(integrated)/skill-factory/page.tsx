import nextDynamic from "next/dynamic";
import { Suspense } from "react";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const SkillFactoryPageClient = nextDynamic(
  () =>
    import("@/components/apps-tools/skill-factory-page-client").then((mod) => ({
      default: mod.SkillFactoryPageClient,
    })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function SkillFactoryModulePage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <SkillFactoryPageClient />
    </Suspense>
  );
}
