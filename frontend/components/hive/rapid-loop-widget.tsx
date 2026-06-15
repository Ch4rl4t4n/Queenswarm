"use client";

import { Loader2Icon, Zap } from "lucide-react";
import { useCallback, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS } from "@/lib/cockpit-poll-profile";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { RapidLoopStageRow, RapidLoopSummaryPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function stageTone(status: RapidLoopStageRow["status"]): "ok" | "warn" | "err" | "info" {
  if (status === "active") {
    return "info";
  }
  if (status === "ok") {
    return "ok";
  }
  if (status === "warn") {
    return "warn";
  }
  return "warn";
}

function fmtSec(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  if (value < 1) {
    return "<1s";
  }
  return `${Math.round(value)}s`;
}

/** Dashboard widget — scrape → reflect → simulate → reward under SLA. */
export function RapidLoopWidget({ eager = false }: { eager?: boolean }): JSX.Element {
  const [payload, setPayload] = useState<RapidLoopSummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<RapidLoopSummaryPayload>("dashboard/rapid-loop?window_hours=24");
      setPayload(body);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Rapid loop telemetry unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void load(), COCKPIT_POLL_COLONY_TELEMETRY_MS, {
    initialDelayMs: eager ? 0 : DASHBOARD_BOOT_STAGGER_MS.rapidLoop,
  });

  const slaPct = payload?.sla_met_pct;
  const slaOk = slaPct == null || slaPct >= 80;

  return (
    <div data-testid="rapid-loop-widget">
    <V4Card className="v4-card-interactive">
      <V4CardHeader
        title="Rapid learning loop"
        description="Scrape → reflect → simulate → reward"
        actions={
          <V4Badge tone={payload?.loop_healthy ? "ok" : "warn"}>
            <Zap className="mr-1 inline h-3 w-3" aria-hidden />
            {payload?.loop_healthy ? "verified" : "warming"}
          </V4Badge>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Measuring loop SLA…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && payload ? (
        <>
          <div className="mb-4 flex flex-wrap gap-3 text-xs text-(--qs-text-2)">
            <span>
              SLA target <span className="font-mono text-pollen">{payload.sla_target_sec}s</span>
            </span>
            <span>
              Avg cycle <span className="font-mono text-cyan">{fmtSec(payload.avg_cycle_sec)}</span>
            </span>
            <span className={cn(!slaOk && "text-(--qs-magenta)")}>
              SLA met{" "}
              <span className="font-mono">{slaPct != null ? `${slaPct.toFixed(0)}%` : "—"}</span>
            </span>
          </div>

          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {(payload.stages ?? []).map((stage, index) => (
              <li
                key={stage.id}
                className="rounded-xl border border-(--qs-border) bg-black/20 px-3 py-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-(--qs-text-3)">
                    {index + 1}. {stage.label}
                  </span>
                  <V4Badge tone={stageTone(stage.status)}>{stage.status}</V4Badge>
                </div>
                <p className="mt-1 font-mono text-lg text-(--qs-text)">{stage.count_24h}</p>
                <p className="text-[10px] text-(--qs-text-3)">
                  {stage.last_at ? new Date(stage.last_at).toLocaleTimeString("sk-SK") : "no activity"}
                </p>
              </li>
            ))}
          </ol>

          {payload.last_cycle_at ? (
            <p className="mt-3 text-[10px] text-(--qs-text-3)">
              Last verified cycle {fmtSec(payload.last_cycle_sec)} ·{" "}
              {new Date(payload.last_cycle_at).toLocaleString("sk-SK")}
            </p>
          ) : null}

          {payload.pattern_telemetry && payload.pattern_telemetry.top_patterns.length > 0 ? (
            <div className="mt-4 rounded-xl border border-cyan/20 bg-cyan/5 p-3">
              <p className="text-[11px] uppercase tracking-wide text-cyan">Pattern telemetry</p>
              <p className="mt-1 text-xs text-(--qs-text-2)">
                {payload.pattern_telemetry.sessions_analyzed} verified sessions ·{" "}
                {payload.pattern_telemetry.patterns_tracked} patterns tracked
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {payload.pattern_telemetry.top_patterns.slice(0, 6).map((row) => (
                  <V4Badge
                    key={row.id}
                    tone={
                      row.success_rate_pct == null
                        ? "info"
                        : row.success_rate_pct >= 70
                          ? "ok"
                          : "warn"
                    }
                  >
                    {row.label}{" "}
                    {row.success_rate_pct != null ? `${row.success_rate_pct.toFixed(0)}%` : "—"}
                  </V4Badge>
                ))}
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </V4Card>
    </div>
  );
}
