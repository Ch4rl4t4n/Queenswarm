"use client";

import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { DumpSleepPanel } from "@/components/ballroom/dump-sleep-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4PageCanvas } from "@/components/ui/v4";

export function BallroomPageClient() {
  return (
    <V4PageCanvas className="v4-page-canvas--ballroom min-h-0 flex-1 gap-2 lg:gap-4">
      <HivePageHeader
        className="mb-0 shrink-0"
        title="Ballroom"
        subtitle="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
      />
      <DumpSleepPanel />
      <BallroomPanel variant="v4" showHeader={false} />
    </V4PageCanvas>
  );
}
