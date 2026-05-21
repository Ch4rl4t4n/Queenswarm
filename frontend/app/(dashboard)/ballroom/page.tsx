import nextDynamic from "next/dynamic";

import { SettingsPanelSkeleton } from "@/components/hive/settings-panel-skeleton";

const BallroomPageClient = nextDynamic(
  () => import("@/components/hive/ballroom-page-client").then((mod) => ({ default: mod.BallroomPageClient })),
  { loading: () => <SettingsPanelSkeleton /> },
);

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return <BallroomPageClient />;
}
