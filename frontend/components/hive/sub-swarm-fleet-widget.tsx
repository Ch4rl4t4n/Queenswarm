"use client";

import Link from "next/link";
import { Hexagon, Loader2Icon, RadioIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { SubSwarmFleetPayload } from "@/lib/hive-types";
import { formatSyncDue, memberCapacityTone, syncTone } from "@/lib/sub-swarm-local-mind-utils";
import { cn } from "@/lib/utils";

/** FP3 — Fleet view: up to 10 colonies with 5 min global sync rings. */
export function SubSwarmFleetWidget({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<SubSwarmFleetPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [syncBusy, setSyncBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<SubSwarmFleetPayload>("dashboard/sub-swarm-fleet");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Sub-swarm fleet unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  const syncDue = useCallback(async () => {
    setSyncBusy(true);
    try {
      const result = await hivePostJson<{ message?: string; synced_count?: number }>(
        "dashboard/sub-swarm-fleet/sync-due",
        {},
      );
      toast.success(result.message ?? "Global sync recorded.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Batch sync failed.");
    } finally {
      setSyncBusy(false);
    }
  }, [load]);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.subSwarmFleet,
  });

  const intervalMin = payload ? Math.max(1, Math.round(payload.hive_sync_interval_sec / 60)) : 5;
  const dueCount = payload?.due_sync_count ?? 0;

  return (
    <div data-testid="sub-swarm-fleet-widget">
      <V4Card className="v4-card-interactive">
        <V4CardHeader
          title="Sub-swarm fleet"
          description={`Local hive minds · global sync every ${intervalMin} min`}
          actions={
            payload?.enabled ? (
              <V4Badge tone={dueCount > 0 ? "warn" : "ok"}>
                <RadioIcon className="mr-1 inline h-3 w-3" aria-hidden />
                {dueCount > 0 ? `${dueCount} due` : "in cadence"}
              </V4Badge>
            ) : null
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading fleet telemetry…
          </p>
        ) : null}

        {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

        {!loading && !err && payload?.enabled ? (
          <>
            <div className="mb-4 flex flex-wrap gap-3 text-xs text-(--qs-text-2)">
              <span>
                Colonies{" "}
                <span className="font-mono text-cyan">{payload.colony_count}</span>
              </span>
              <span>
                Bees{" "}
                <span className="font-mono text-pollen">{payload.total_bees}</span>
              </span>
              <span className={cn(dueCount > 0 && "text-(--qs-magenta)")}>
                Sync due{" "}
                <span className="font-mono">{dueCount}</span>
              </span>
            </div>

            {payload.colonies.length === 0 ? (
              <p className="text-sm text-(--qs-text-3)">{payload.operator_hint}</p>
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2">
                {payload.colonies.map((colony) => (
                  <li
                    key={colony.id}
                    className="rounded-xl border border-(--qs-border) bg-black/20 px-3 py-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <Link
                          href={colony.workspace_href}
                          className="truncate text-sm font-medium text-(--qs-text) hover:text-cyan"
                        >
                          {colony.display_name}
                        </Link>
                        <p className="text-[10px] text-(--qs-text-3)">
                          {colony.lane_label} ·{" "}
                          <span className={cn("font-mono", memberCapacityTone(colony.member_count, colony.recommended_bee_count) === "warn" && "text-(--qs-magenta)")}>
                            {colony.member_count}/{colony.recommended_bee_count} bees
                          </span>
                        </p>
                      </div>
                      <V4Badge tone={syncTone(colony.needs_sync)}>
                        {colony.needs_sync ? "due" : "local"}
                      </V4Badge>
                    </div>

                    <div className="relative mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          colony.needs_sync ? "bg-pollen" : "bg-success",
                        )}
                        style={{ width: `${colony.sync_progress_pct}%` }}
                      />
                    </div>

                    <p className="mt-1 text-[10px] text-(--qs-text-3)">
                      next sync in{" "}
                      <span className="font-mono text-cyan">{formatSyncDue(colony.sync_due_in_sec)}</span>
                    </p>
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {dueCount > 0 ? (
                <HiveRefreshButton
                  busy={syncBusy}
                  label="Sync due colonies"
                  onClick={() => void syncDue()}
                />
              ) : null}
              <Link
                href={payload.swarms_href}
                className="qs-btn qs-btn--ghost qs-btn--sm inline-flex min-h-[36px] items-center gap-1"
              >
                <Hexagon className="h-3.5 w-3.5" aria-hidden />
                All swarms
              </Link>
            </div>

            {payload.operator_hint ? (
              <p className="mt-3 text-[10px] text-(--qs-text-3)">{payload.operator_hint}</p>
            ) : null}
          </>
        ) : null}

        {!loading && !err && payload && !payload.enabled ? (
          <p className="text-sm text-(--qs-text-3)">{payload.operator_hint}</p>
        ) : null}
      </V4Card>
    </div>
  );
}
