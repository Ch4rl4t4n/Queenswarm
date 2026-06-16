"use client";

import { Download, FileText, Loader2, Presentation } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet, hivePostJson } from "@/lib/api";

interface ExportLaneSnapshot {
  enabled: boolean;
  destinations: string[];
  default_mode: string;
  notion_configured: boolean;
  slides_configured: boolean;
  critic_min_score_label: string;
  operator_hint: string;
}

interface ExportPreview {
  ok: boolean;
  deliverable_id: string | null;
  report_title: string | null;
  destination: string;
  mode: string;
  critic_score: number | null;
  critic_score_label: string | null;
  critic_passed: boolean;
  export_ready: boolean;
  notion_payload: Record<string, unknown> | null;
  slides_payload: Record<string, unknown> | null;
  lineage_count: number;
  chart_count: number;
  operator_hint: string;
}

interface ExportSubmitResult {
  ok: boolean;
  deliverable_id: string | null;
  destination: string;
  mode: string;
  simulated: boolean;
  critic_passed: boolean;
  message: string;
  notion_result: Record<string, unknown> | null;
  slides_result: Record<string, unknown> | null;
}

type ExportDestination = "notion" | "slides";

export function AnalyticsExportLanePanel(): JSX.Element | null {
  const [snapshot, setSnapshot] = useState<ExportLaneSnapshot | null>(null);
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [submitResult, setSubmitResult] = useState<ExportSubmitResult | null>(null);
  const [destination, setDestination] = useState<ExportDestination>("notion");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<ExportLaneSnapshot>("analytics-workspace/export-lane");
      setSnapshot(data);
    } catch {
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const runPreview = useCallback(async (dest: ExportDestination) => {
    setBusy(true);
    setSubmitResult(null);
    try {
      const data = await hivePostJson<ExportPreview>("analytics-workspace/export-lane/preview", {
        destination: dest,
        mode: "simulate",
      });
      setPreview(data);
    } catch {
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }, []);

  const runSubmit = useCallback(async () => {
    setBusy(true);
    try {
      const data = await hivePostJson<ExportSubmitResult>("analytics-workspace/export-lane/submit", {
        destination,
        mode: "simulate",
      });
      setSubmitResult(data);
    } catch {
      setSubmitResult(null);
    } finally {
      setBusy(false);
    }
  }, [destination]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (snapshot?.enabled) {
      void runPreview(destination);
    }
  }, [snapshot?.enabled, destination, runPreview]);

  if (loading) {
    return (
      <V4Card data-testid="analytics-export-lane-loading">
        <div className="flex items-center gap-2 p-4 text-sm text-(--qs-text-3)">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading export lane…
        </div>
      </V4Card>
    );
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div data-testid="analytics-export-lane">
      <V4Card id="analytics-export">
      <V4CardHeader
        kicker="DA8 · Export lane"
        title="Export inbox"
        description={snapshot.operator_hint}
        actions={
          <div className="flex items-center gap-2">
            <V4Badge tone="info">min {snapshot.critic_min_score_label}</V4Badge>
            <HiveRefreshButton busy={loading || busy} onClick={() => void load()} />
          </div>
        }
      />

      <div className="flex flex-wrap gap-2 px-4 pb-3">
        <button
          type="button"
          className={`qs-btn qs-btn--sm ${destination === "notion" ? "qs-btn--primary" : "qs-btn--ghost"}`}
          onClick={() => setDestination("notion")}
          data-testid="analytics-export-dest-notion"
        >
          <FileText className="h-3.5 w-3.5" aria-hidden />
          Notion page
        </button>
        <button
          type="button"
          className={`qs-btn qs-btn--sm ${destination === "slides" ? "qs-btn--primary" : "qs-btn--ghost"}`}
          onClick={() => setDestination("slides")}
          data-testid="analytics-export-dest-slides"
        >
          <Presentation className="h-3.5 w-3.5" aria-hidden />
          Google Slides
        </button>
      </div>

      <div className="grid gap-3 px-4 pb-4 lg:grid-cols-2">
        <article className="rounded-lg border border-white/10 bg-black/25 p-4">
          <h3 className="text-sm font-semibold text-(--qs-text)">Connector readiness</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <V4Badge tone={snapshot.notion_configured ? "ok" : "warn"}>
              Notion {snapshot.notion_configured ? "ready" : "configure"}
            </V4Badge>
            <V4Badge tone={snapshot.slides_configured ? "ok" : "warn"}>
              Slides {snapshot.slides_configured ? "ready" : "via Sheets OAuth"}
            </V4Badge>
          </div>
          <Link href="/integrations?tab=hub&hubSection=roster" className="qs-btn qs-btn--ghost qs-btn--sm mt-3">
            Open Integrations
          </Link>
        </article>

        <article className="rounded-lg border border-white/10 bg-black/25 p-4" data-testid="analytics-export-preview">
          {!preview?.ok ? (
            <>
              <h3 className="text-sm font-semibold text-(--qs-text)">No report to export</h3>
              <p className="mt-2 text-xs text-(--qs-text-3)">{preview?.operator_hint ?? snapshot.operator_hint}</p>
              <Link
                href="/apps-tools/analytics?section=question#analytics-question"
                className="qs-btn qs-btn--primary qs-btn--sm mt-3"
              >
                Dispatch business question
              </Link>
            </>
          ) : (
            <>
              <h3 className="text-sm font-semibold text-(--qs-text)">{preview.report_title}</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                <V4Badge tone={preview.critic_passed ? "ok" : "warn"}>
                  critic {preview.critic_score_label ?? "missing"}
                </V4Badge>
                <V4Badge tone="info">{preview.chart_count} charts</V4Badge>
                <V4Badge tone="info">{preview.lineage_count} lineage</V4Badge>
              </div>
              <p className="mt-2 text-xs text-(--qs-text-3)">{preview.operator_hint}</p>
              <button
                type="button"
                className="qs-btn qs-btn--primary qs-btn--sm mt-3 inline-flex items-center gap-1"
                disabled={!preview.export_ready || busy}
                onClick={() => void runSubmit()}
                data-testid="analytics-export-submit"
              >
                <Download className="h-3.5 w-3.5" aria-hidden />
                Stage simulate export
              </button>
            </>
          )}
        </article>
      </div>

      {submitResult?.ok ? (
        <p className="px-4 pb-4 text-sm text-green" data-testid="analytics-export-result">
          {submitResult.message}
        </p>
      ) : null}
      </V4Card>
    </div>
  );
}
