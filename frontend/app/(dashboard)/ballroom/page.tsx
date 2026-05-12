import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";

export const dynamic = "force-dynamic";

export default function BallroomRoute() {
  return (
    <div className="space-y-8">
      <HivePageHeader title="Ballroom • Voice Sessions" subtitle="Multi-agent voice rooms · WebRTC · live transcript lane" />
      <BallroomPanel />
    </div>
  );
}
