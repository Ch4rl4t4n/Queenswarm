"use client";

import Link from "next/link";
import { LayoutDashboard, Users } from "lucide-react";
import { useState } from "react";

import { BallroomPanel } from "@/components/ballroom/ballroom-panel";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { V4PageCanvas } from "@/components/ui/v4";
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
    <V4PageCanvas className="v4-page-canvas--ballroom min-h-0 flex-1 overflow-hidden gap-3 lg:gap-4">
      <HivePageHeader
        className="mb-0 shrink-0 max-lg:hidden"
        title="Ballroom"
        subtitle="Realtime voice + chat lane integrated with supervisor sessions and live swarm orchestration."
        actions={
          <>
            <Link href="/agents#sessions" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <Users className="h-4 w-4" aria-hidden />
              Supervisor sessions
            </Link>
            <Link href="/" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
              <LayoutDashboard className="h-4 w-4" aria-hidden />
              Dashboard
            </Link>
          </>
        }
        status={
          <span className="inline-flex items-center gap-2 font-mono text-xs">
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
      <div className="flex shrink-0 items-center justify-between gap-2 rounded-xl border border-(--qs-border) bg-black/40 px-3 py-2 lg:hidden">
        <h1 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-(--qs-text)">Ballroom</h1>
        <span className="inline-flex items-center gap-2 font-mono text-[11px] text-(--qs-text-3)">
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
      </div>
      <BallroomPanel variant="v4" showHeader={false} onStatusChange={setWsStatus} />
    </V4PageCanvas>
  );
}
