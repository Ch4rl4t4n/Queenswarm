import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const ForagersPageClient = nextDynamic(
  () => import("@/components/hive/foragers-page-client").then((mod) => ({ default: mod.ForagersPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function ForagersPage() {
  return <ForagersPageClient />;
}
