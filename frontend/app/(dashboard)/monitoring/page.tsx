import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const MonitoringPageClient = nextDynamic(
  () => import("@/components/hive/monitoring-page-client").then((mod) => ({ default: mod.MonitoringPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function MonitoringPage(): JSX.Element {
  return <MonitoringPageClient />;
}
