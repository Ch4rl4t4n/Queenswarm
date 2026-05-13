import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return (
    <div className="space-y-8">
      <HivePageHeader title="Ballroom" subtitle="Live transcript a hlas po misii z dashboardu." />
      <BallroomPanel />
    </div>
  );
}
