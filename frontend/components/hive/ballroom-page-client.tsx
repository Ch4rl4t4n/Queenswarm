"use client";

import Link from "next/link";
import { LayoutDashboard, Plug, Users } from "lucide-react";
import { useState } from "react";

import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { DumpSleepPanel } from "@/components/ballroom/dump-sleep-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4PageCanvas } from "@/components/ui/v4";
import { integrationsTabHref } from "@/lib/integrations-routes";
import { cn } from "@/lib/utils";

interface BallroomWsStatus {
  connected: boolean;
  error: string | null;
  sessionBound: boolean;
}

export function BallroomPageClient() {
  const [wsStatus, setWsStatus] = useState<BallroomWsStatus>({
    connected: false,
    error: null,
    sessionBound: false,
  });

  const wsLabel = wsStatus.error
    ? "WS error"
    : wsStatus.connected
      ? "WS live"
      : wsStatus.sessionBound
        ? "WS connecting"
        : "WS idle";

  return (
    <V4PageCanvas className="v4-page-canvas--ballroom min-h-0 flex-1 gap-2 lg:gap-4">
      <HivePageHeader
        className="mb-0 shrink-0"
        title="Ballroom"
        subtitle="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
        actions={
          <div className="max-lg:hidden flex flex-wrap items-center gap-3">
            <Link href={integrationsTabHref("active", "ecosystem")} className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Plug className="h-4 w-4" aria-hidden />
              Integrations
            </Link>
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Users className="h-4 w-4" aria-hidden />
              Supervisor sessions
            </Link>
            <Link href="/" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <LayoutDashboard className="h-4 w-4" aria-hidden />
              Dashboard
            </Link>
          </div>
        }
        status={
          <span className="ballroom-ws-status inline-flex items-center gap-2 font-mono text-xs">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                wsStatus.error
                  ? "bg-(--qs-red)"
                  : wsStatus.connected
                    ? "bg-(--qs-green) shadow-[0_0_8px_rgba(0,255,136,0.6)]"
                    : "bg-(--qs-text-3)",
              )}
              aria-hidden
            />
            {wsLabel}
          </span>
        }
      />
      <DumpSleepPanel />
      <BallroomPanel variant="v4" showHeader={false} onStatusChange={setWsStatus} />
    </V4PageCanvas>
  );
}
