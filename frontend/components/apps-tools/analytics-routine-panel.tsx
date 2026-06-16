"use client";

import { CalendarClock, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet, hivePostJson } from "@/lib/api";

interface RoutineKpi {
  enabled: boolean;
  routine_status: string;
  routine_id: string | null;
  routine_name: string;
  next_run_at: string | null;
  last_run_at: string | null;
  last_session_status: string | null;
  last_session_href: string | null;
  report_title: string | null;
  critic_score_label: string | null;
  critic_passed: boolean;
  export_ready: boolean;
  connector_ready_count: number;
  morning_brief_line: string;
  operator_hint: string;
  workspace_href: string;
}

function statusTone(status: string): "ok" | "warn" | "info" | "purple" {
  if (status === "ready") return "ok";
  if (status === "running") return "info";
  if (status === "missing") return "warn";
  return "purple";
}

export function AnalyticsRoutinePanel(): JSX.Element | null {
  const [kpi, setKpi] = useState<RoutineKpi | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<RoutineKpi>("analytics-workspace/routine");
      setKpi(data);
    } catch {
      setKpi(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const bootstrap = useCallback(async () => {
    setBusy(true);
    try {
      await hivePostJson("analytics-workspace/routine/bootstrap", {});
      await load();
    } finally {
      setBusy(false);
    }
  }, [load]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div data-testid="analytics-routine-loading">
        <V4Card>
          <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading weekly routine…
          </div>
        </V4Card>
      </div>
    );
  }

  if (!kpi?.enabled) {
    return null;
  }

  return (
    <div data-testid="analytics-routine-panel">
      <V4Card>
        <V4CardHeader
          kicker="DA9 · Weekly routine"
          title={kpi.routine_name}
          description={kpi.operator_hint}
          actions={
            <div className="flex items-center gap-2">
              <V4Badge tone={statusTone(kpi.routine_status)}>{kpi.routine_status}</V4Badge>
              <HiveRefreshButton busy={loading || busy} onClick={() => void load()} />
            </div>
          }
        />
        <div className="space-y-3 px-4 pb-4">
          <p className="text-sm text-(--qs-text-2)">{kpi.morning_brief_line}</p>
          <div className="flex flex-wrap gap-2">
            <V4Badge tone="info">{kpi.connector_ready_count} connectors ready</V4Badge>
            {kpi.critic_score_label ? (
              <V4Badge tone={kpi.critic_passed ? "ok" : "warn"}>critic {kpi.critic_score_label}</V4Badge>
            ) : null}
            {kpi.export_ready ? <V4Badge tone="ok">export ready</V4Badge> : null}
          </div>
          {kpi.report_title ? (
            <p className="text-xs text-(--qs-text-3)">
              Latest report: <span className="font-medium text-(--qs-text)">{kpi.report_title}</span>
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {kpi.routine_status === "missing" ? (
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1"
                disabled={busy}
                onClick={() => void bootstrap()}
                data-testid="analytics-routine-bootstrap"
              >
                <CalendarClock className="h-3.5 w-3.5" aria-hidden />
                Schedule weekly deck
              </button>
            ) : null}
            {kpi.last_session_href ? (
              <Link href={kpi.last_session_href} className="qs-btn qs-btn--ghost qs-btn--sm">
                Open last session
              </Link>
            ) : null}
            <Link
              href="/apps-tools/analytics?section=export#analytics-export"
              className="qs-btn qs-btn--ghost qs-btn--sm"
            >
              Export inbox
            </Link>
          </div>
        </div>
      </V4Card>
    </div>
  );
}
