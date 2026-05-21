import { Suspense } from "react";

import { SwarmBuilderWizard } from "@/components/hive/swarm-builder-wizard";
import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

export default function SwarmBuilderPage(): JSX.Element {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <SwarmBuilderWizard />
    </Suspense>
  );
}
