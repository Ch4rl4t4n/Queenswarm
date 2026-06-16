"use client";

import { Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet, hivePostJson } from "@/lib/api";

interface ReportCriticSnapshot {
  enabled: boolean;
  has_artifact: boolean;
  deliverable_id: string | null;
  report_title: string | null;
  preset_id: string;
  preset_label: string;
  rubric_template_id: string;
  min_score_label: string;
  critic_score: number | null;
  critic_score_label: string | null;
  critic_passed: boolean;
  export_ready: boolean;
  last_run_at: string | null;
  turns_used: number | null;
  operator_hint: string;
}

interface ReportCriticRunResult {
  ok: boolean;
  passed: boolean;
  deliverable_id: string | null;
  report_title: string | null;
  critic_score_label: string | null;
  export_ready: boolean;
  turns_used: number;
  message: string;
}

export function AnalyticsReportCriticPanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ReportCriticSnapshot | null>(null);
  const [runResult, setRunResult] = useState<ReportCriticRunResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ReportCriticSnapshot>("analytics-workspace/report-critic");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const runCritic = useCallback(async () => {
    setBusy(true);
    setRunResult(null);
    try {
      const data = await hivePostJson<ReportCriticRunResult>("analytics-workspace/report-critic/run", {});
      setRunResult(data);
      await load();
    } catch {
      setRunResult(null);
    } finally {
      setBusy(false);
    }
  }, [load]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div data-testid="analytics-report-critic-loading">
        <V4Card>
          <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading report critic…
          </div>
        </V4Card>
      </div>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  const scoreTone = snapshot.critic_passed ? "ok" : snapshot.critic_score != null ? "warn" : "info";

  return (
    <div id="analytics-report-critic" data-testid="analytics-report-critic">
      <V4Card>
        <V4CardHeader
          kicker="DA10 · Report critic"
          title={snapshot.preset_label || "Analytics report critic loop"}
          description={snapshot.operator_hint}
          actions={
            <div className="flex items-center gap-2">
              {snapshot.critic_score_label ? (
                <span data-testid="analytics-report-critic-score">
                  <V4Badge tone={scoreTone}>critic {snapshot.critic_score_label}</V4Badge>
                </span>
              ) : null}
              {snapshot.export_ready ? (
                <span data-testid="analytics-report-critic-export-ready">
                  <V4Badge tone="ok">export ready</V4Badge>
                </span>
              ) : null}
              <HiveRefreshButton busy={loading || busy} onClick={() => void load()} />
            </div>
          }
        />
        <div className="space-y-3 px-4 pb-4">
          {snapshot.has_artifact && snapshot.report_title ? (
            <p className="text-sm text-(--qs-text-2)">
              Report: <span className="font-medium text-(--qs-text-1)">{snapshot.report_title}</span>
              {" · "}
              rubric <code className="text-xs">{snapshot.rubric_template_id}</code>
              {" · "}
              floor {snapshot.min_score_label}
            </p>
          ) : (
            <p className="text-sm text-(--qs-text-3)">
              No artifact yet —{" "}
              <Link href="/apps-tools/analytics?section=question" className="text-cyan hover:underline">
                dispatch a business question
              </Link>{" "}
              first.
            </p>
          )}

          {snapshot.last_run_at ? (
            <p className="text-xs text-(--qs-text-3)">
              Last run {new Date(snapshot.last_run_at).toLocaleString()}
              {snapshot.turns_used != null ? ` · ${snapshot.turns_used} turn(s)` : ""}
            </p>
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="analytics-report-critic-run"
              disabled={busy || !snapshot.has_artifact}
              onClick={() => void runCritic()}
              className="inline-flex items-center gap-2 rounded-md border border-cyan/40 bg-cyan/10 px-3 py-1.5 text-sm font-medium text-cyan hover:bg-cyan/20 disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
              Run closed loop
            </button>
            {snapshot.export_ready ? (
              <Link
                href="/apps-tools/analytics?section=export"
                className="text-sm text-cyan hover:underline"
                data-testid="analytics-report-critic-export-link"
              >
                Open export lane →
              </Link>
            ) : null}
          </div>

          {runResult ? (
            <p
              data-testid="analytics-report-critic-result"
              className={`text-sm ${runResult.passed ? "text-(--qs-success)" : "text-(--qs-text-2)"}`}
            >
              {runResult.message}
            </p>
          ) : null}
        </div>
      </V4Card>
    </div>
  );
}
