"use client";

import { Info, Loader2Icon, X } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge } from "@/components/ui/v4";
import { HiveModalShell, hiveModalBottomSheetPanelClass, hiveModalScrollBodyClass } from "@/components/hive/hive-modal-shell";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface DreamCycleRow {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  items_processed: number;
  items_deduplicated: number;
  items_consolidated: number;
}

interface DreamCycleInsight {
  id: string;
  source_kind: string;
  source_ref: string;
  summary: string;
  confidence: number;
}

interface DreamCycleDetail extends DreamCycleRow {
  digest_md: string;
  dream_report: {
    summary?: string;
    success_strategies?: string[];
    repeated_errors?: string[];
    improvement_proposals?: string[];
    generated_at?: string;
  };
  insights: DreamCycleInsight[];
}

function cycleStatusTone(status: string): "ok" | "warn" | "err" | "info" {
  const s = status.toLowerCase();
  if (s.includes("complete") || s.includes("success")) {
    return "ok";
  }
  if (s.includes("fail") || s.includes("error")) {
    return "err";
  }
  if (s.includes("run") || s.includes("queue") || s.includes("pending")) {
    return "info";
  }
  return "warn";
}

function formatCycleWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("sk-SK");
}

interface DreamReportInfoDialogProps {
  cycleId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Full dream cycle digest — markdown summary, structured report, and insight rows. */
export function DreamReportInfoDialog({ cycleId, open, onOpenChange }: DreamReportInfoDialogProps): JSX.Element | null {
  const [detail, setDetail] = useState<DreamCycleDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !cycleId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setDetail(null);
    void hiveGet<DreamCycleDetail>(`dreaming/cycles/${encodeURIComponent(cycleId)}`)
      .then((body) => {
        if (!cancelled) {
          setDetail(body);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          toast.error(err instanceof HiveApiError ? err.message : "Dream report detail unavailable");
          onOpenChange(false);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [cycleId, onOpenChange, open]);

  if (!open || !cycleId) {
    return null;
  }

  const report = detail?.dream_report ?? {};

  return (
    <HiveModalShell
      open
      onClose={() => onOpenChange(false)}
      labelledBy="dream-report-info-title"
      align="bottom-sheet"
      zIndexClass="z-[72]"
      closeLabel="Close dream report"
      panelClassName={cn(hiveModalBottomSheetPanelClass, "max-h-[min(92dvh,920px)] max-w-3xl")}
    >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4 sm:px-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Info className="h-4 w-4 shrink-0 text-pollen" aria-hidden />
              <h2 id="dream-report-info-title" className="text-lg font-semibold text-(--qs-text)">
                Dream report
              </h2>
              {detail ? <V4Badge tone={cycleStatusTone(detail.status)}>{detail.status}</V4Badge> : null}
            </div>
            {detail ? (
              <p className="mt-1 text-sm text-(--qs-text-2)">{formatCycleWhen(detail.started_at)}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
            aria-label="Close dream report"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </header>

        <div className={cn(hiveModalScrollBodyClass, "space-y-4")}>
          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-(--qs-text-3)">
              <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
              Loading dream report…
            </div>
          ) : detail ? (
            <>
              <section className="qs-bubble-inner space-y-2 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Run metrics</p>
                <dl className="grid gap-2 text-xs sm:grid-cols-2">
                  <div>
                    <dt className="text-(--qs-text-4)">Processed</dt>
                    <dd className="text-(--qs-text)">{detail.items_processed}</dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Consolidated</dt>
                    <dd className="text-(--qs-text)">{detail.items_consolidated}</dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Deduplicated</dt>
                    <dd className="text-(--qs-text)">{detail.items_deduplicated}</dd>
                  </div>
                  <div>
                    <dt className="text-(--qs-text-4)">Finished</dt>
                    <dd className="text-(--qs-text)">
                      {detail.finished_at ? formatCycleWhen(detail.finished_at) : "—"}
                    </dd>
                  </div>
                </dl>
              </section>

              {report.summary ? (
                <section className="v4-dream-report-context">
                  <p className="v4-field-label text-[10px] text-cyan-300/90">What this report is about</p>
                  <p className="hive-readable-prose mt-1 text-sm leading-relaxed text-(--qs-text-2)">{report.summary}</p>
                </section>
              ) : null}

              {detail.digest_md?.trim() ? (
                <section className="qs-bubble-inner space-y-2 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">Digest</p>
                  <pre className="hive-readable-prose whitespace-pre-wrap font-(family-name:--font-jetbrains-mono) text-xs leading-relaxed text-(--qs-text-2)">
                    {detail.digest_md.trim()}
                  </pre>
                </section>
              ) : null}

              {report.success_strategies?.length ? (
                <ReportListSection title="Successful patterns" items={report.success_strategies} tone="ok" />
              ) : null}
              {report.repeated_errors?.length ? (
                <ReportListSection title="Repeated errors" items={report.repeated_errors} tone="err" />
              ) : null}
              {report.improvement_proposals?.length ? (
                <ReportListSection title="Improvement proposals" items={report.improvement_proposals} tone="gold" />
              ) : null}

              {detail.insights.length > 0 ? (
                <section className="qs-bubble-inner space-y-2 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                    Consolidated insights ({detail.insights.length})
                  </p>
                  <ul className="space-y-2">
                    {detail.insights.slice(0, 12).map((insight) => (
                      <li key={insight.id} className="hive-readable-card rounded-(--qs-radius-sm) border border-(--qs-border) px-3 py-2.5 sm:px-4">
                        <p className="hive-readable-prose text-xs leading-relaxed text-(--qs-text-2)">{insight.summary}</p>
                        <p className="mt-1 font-mono text-[10px] text-(--qs-text-3)">
                          {insight.source_kind} · confidence {Math.round(insight.confidence * 100)}%
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          ) : null}
        </div>
    </HiveModalShell>
  );
}

function ReportListSection({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "ok" | "err" | "gold";
}): JSX.Element {
  const toneClass =
    tone === "ok" ? "text-(--qs-green)" : tone === "err" ? "text-(--qs-red)" : "text-pollen";
  return (
    <section className="qs-bubble-inner space-y-2 p-3">
      <p className={cn("text-[11px] font-semibold uppercase tracking-wider", toneClass)}>{title}</p>
      <ul className="hive-readable-prose list-disc space-y-1 pl-4 text-xs leading-relaxed text-(--qs-text-2)">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
