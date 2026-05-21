"use client";

import { ClockIcon, Loader2Icon } from "lucide-react";
import { useCallback, useState } from "react";

import { V4Badge, V4Card, V4CardHeader, V4Stat } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { TimeSavedSummaryPayload } from "@/lib/hive-types";

function fmtHours(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (value < 1) {
    return `${Math.round(value * 60)}m`;
  }
  return `${value.toFixed(1)}h`;
}

/** Verified workflow ROI — hours saved by template, recipe, or custom tasks. */
export function TimeSavedPanel(): JSX.Element {
  const [payload, setPayload] = useState<TimeSavedSummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<TimeSavedSummaryPayload>("dashboard/time-saved?window_days=30");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Time saved analytics unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: DASHBOARD_BOOT_STAGGER_MS.timeSaved,
  });

  return (
    <V4Card className="v4-card-interactive">
      <V4CardHeader
        title="Time saved"
        description="Verified workflows · template ROI estimates"
        actions={
          <V4Badge tone="ok">
            <ClockIcon className="mr-1 inline h-3 w-3" aria-hidden />
            30d
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Calculating ROI…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && payload ? (
        <>
          <div className="v4-stat-grid mt-2">
            <V4Stat
              label="Hours saved"
              value={fmtHours(payload.hours_saved_total)}
              foot={`${payload.verified_task_count} verified tasks`}
              valueVariant="gold"
            />
            <V4Stat
              label="Projected / month"
              value={fmtHours(payload.hours_saved_projected_monthly)}
              foot="Scaled from window"
            />
          </div>

          {payload.breakdown.length === 0 ? (
            <p className="mt-4 text-sm text-(--qs-text-3)">
              No verified tasks with pollen in the last {payload.window_days} days yet.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {payload.breakdown.slice(0, 6).map((row) => (
                <li key={`${row.source_kind}:${row.source_key}`} className="rounded-xl border border-(--qs-border) bg-black/20 px-3 py-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm text-(--qs-text)">{row.source_label}</span>
                    <span className="font-mono text-sm text-pollen">{fmtHours(row.hours_saved)}</span>
                  </div>
                  <p className="mt-1 text-[11px] text-(--qs-text-3)">
                    {row.task_count} tasks · ~{Math.round(row.minutes_per_task)} min each · {row.source_kind}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <p className="mt-3 text-[10px] text-(--qs-text-3)">{payload.disclaimer}</p>
        </>
      ) : null}
    </V4Card>
  );
}
