"use client";

import Link from "next/link";
import { Loader2, Pause, Play, RefreshCw, Rocket } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { FourLaneDigestInboxPanel } from "@/components/hive/four-lane-digest-inbox-panel";
import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";

export interface FourLaneRoutine {
  lane_id: string;
  routine_id: string | null;
  routine_name: string | null;
  is_active: boolean;
  schedule_cron: string | null;
  last_session_status: string | null;
}

export interface FourLaneRow {
  lane_id: string;
  label: string;
  description: string;
  operator_hint: string;
  manual_anchor: string;
  routine: FourLaneRoutine;
  approve_href: string;
  sessions_href: string;
  foragers: Array<{ name: string | null; is_active: boolean; forager_id: string | null }>;
}

interface FourLaneSnapshot {
  enabled: boolean;
  generated_at: string;
  lanes: FourLaneRow[];
  legacy_paused_count: number;
  active_lane_count: number;
}

interface SoloOperatorFourLanesPanelProps {
  onMutate?: () => void;
}

function SoloOperatorFourLanesPanelInner({ onMutate }: SoloOperatorFourLanesPanelProps) {
  const [data, setData] = useState<FourLaneSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const body = await hiveGet<FourLaneSnapshot>("solo-operator/four-lanes");
      setData(body);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Four lanes unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const bootstrap = useCallback(async () => {
    setBusy("bootstrap");
    try {
      const result = await hivePostJson<{ ok: boolean; legacy?: { paused_count?: number } }>(
        "solo-operator/four-lanes/bootstrap",
        { pause_legacy: true },
      );
      if (result.ok) {
        toast.success(`Four lanes ready — paused ${result.legacy?.paused_count ?? 0} legacy routines.`);
        await reload();
        onMutate?.();
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bootstrap failed");
    } finally {
      setBusy(null);
    }
  }, [onMutate, reload]);

  const toggleLane = useCallback(
    async (laneId: string, active: boolean) => {
      setBusy(laneId);
      try {
        await hivePatchJson(`solo-operator/four-lanes/${encodeURIComponent(laneId)}/active`, {
          active,
        });
        toast.success(active ? "Lane resumed" : "Lane paused");
        await reload();
        onMutate?.();
      } catch (e) {
        toast.error(e instanceof HiveApiError ? e.message : "Toggle failed");
      } finally {
        setBusy(null);
      }
    },
    [onMutate, reload],
  );

  if (loading && !data) {
    return (
      <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-(--qs-muted)">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        Loading four lanes…
      </div>
    );
  }

  return (
    <V4Card id="four-lanes">
      <V4CardHeader
        kicker="Solo operator"
        title="Four Lanes"
        description="Four parallel missions — marketing, tech SCV, e-shop, automation. Pause legacy sprawl; approve digests only."
        hint={<InlineSectionHintKey hintKey="fourLanes" />}
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
              disabled={busy !== null}
              onClick={() => void reload()}
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              Refresh
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-1.5"
              disabled={busy === "bootstrap"}
              onClick={() => void bootstrap()}
            >
              {busy === "bootstrap" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <Rocket className="h-3.5 w-3.5" aria-hidden />
              )}
              Bootstrap lanes
            </button>
          </div>
        }
      />
      {data ? (
        <p className="mb-4 text-xs text-(--qs-muted)">
          {data.active_lane_count} active lane routines · {data.legacy_paused_count} legacy routines paused ·{" "}
          <Link href="/manual#four-lanes" className="text-cyan underline">
            Full manual →
          </Link>
        </p>
      ) : null}
      <ul className="space-y-3">
        {(data?.lanes ?? []).map((lane) => {
          const isAutomation = lane.lane_id === "automation";
          const active = lane.routine.is_active;
          return (
            <li
              key={lane.lane_id}
              className="rounded-xl border border-(--qs-border) bg-black/25 p-4"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="text-sm font-semibold text-(--qs-text)">{lane.label}</h4>
                    <V4Badge tone={active ? "ok" : "warn"}>{active ? "ON" : "OFF"}</V4Badge>
                    {lane.routine.schedule_cron ? (
                      <span className="font-mono text-[10px] text-(--qs-text-3)">{lane.routine.schedule_cron}</span>
                    ) : (
                      <span className="text-[10px] text-(--qs-text-3)">manual trigger</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{lane.description}</p>
                  <p className="mt-2 text-[11px] text-(--qs-muted)">{lane.operator_hint}</p>
                  {lane.foragers.length ? (
                    <p className="mt-2 text-[10px] text-(--qs-text-3)">
                      Foragers:{" "}
                      {lane.foragers.map((f) => `${f.name ?? "?"}${f.is_active ? "" : " (off)"}`).join(" · ")}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2 shrink-0">
                  {!isAutomation ? (
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1"
                      disabled={busy === lane.lane_id}
                      onClick={() => void toggleLane(lane.lane_id, !active)}
                    >
                      {active ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                      {active ? "Pause" : "Resume"}
                    </button>
                  ) : null}
                  <Link href={lane.approve_href} className="qs-btn qs-btn--primary qs-btn--sm">
                    Approve
                  </Link>
                  <Link href={lane.sessions_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                    Open
                  </Link>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      <FourLaneDigestInboxPanel />
    </V4Card>
  );
}

export const SoloOperatorFourLanesPanel = memo(SoloOperatorFourLanesPanelInner);
