import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const WorkflowsDagPage = nextDynamic(() => import("@/components/hive/workflows-dag-page"), {
  loading: () => <SettingsPanelSkeleton />,
});

export default function WorkflowsRoutePage(): JSX.Element {
  return <WorkflowsDagPage />;
}
