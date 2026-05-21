import { Suspense } from "react";

import { NewTaskConsole } from "@/components/hive/new-task-console";
import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

export default function NewTaskPage() {
  return (
    <Suspense fallback={<SettingsPanelSkeleton />}>
      <NewTaskConsole />
    </Suspense>
  );
}
