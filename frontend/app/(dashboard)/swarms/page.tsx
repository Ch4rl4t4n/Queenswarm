import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const SwarmsPageClient = nextDynamic(
  () => import("@/components/hive/swarms-page-client").then((mod) => ({ default: mod.SwarmsPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function SwarmsPage() {
  return <SwarmsPageClient />;
}
