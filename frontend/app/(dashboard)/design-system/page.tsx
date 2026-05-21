import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const ComponentShowcase = nextDynamic(
  () => import("@/components/hive/component-showcase").then((mod) => ({ default: mod.ComponentShowcase })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export default function DesignSystemPage() {
  return <ComponentShowcase />;
}
