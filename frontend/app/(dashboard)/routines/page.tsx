import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const RoutinesPageClient = nextDynamic(
  () => import("@/components/hive/routines-page-client").then((mod) => ({ default: mod.RoutinesPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function RoutinesPage() {
  return <RoutinesPageClient />;
}
