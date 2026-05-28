"use client";

import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { DumpSleepPanel } from "@/components/ballroom/dump-sleep-panel";
import { HivePageShell } from "@/components/hive/hive-page-shell";

export function BallroomPageClient() {
  return (
    <HivePageShell
      title="Ballroom"
      subtitle="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
      hintKey="ballroom"
      className="mb-0 shrink-0"
      canvasClassName="v4-page-canvas--ballroom min-h-0 flex-1 gap-2 lg:gap-4"
    >
      <DumpSleepPanel />
      <BallroomPanel variant="v4" showHeader={false} />
    </HivePageShell>
  );
}
