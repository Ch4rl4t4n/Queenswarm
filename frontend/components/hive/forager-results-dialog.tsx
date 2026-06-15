"use client";

import { Download, ExternalLink, FileText, Loader2Icon, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { HiveModalShell, hiveModalScrollBodyClass } from "@/components/hive/hive-modal-shell";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { foragerKnowledgeHref } from "@/lib/execution-lane-routes";
import { formatTimeAgoIso } from "@/lib/format-relative-time";
import { cn } from "@/lib/utils";

export interface ForagerHarvestReportRow {
  forager_id: string;
  name: string;
  description: string;
  source_type: string;
  items_total: number;
  executive_summary: string;
  items: Array<{
    title: string;
    body: string;
    source_url: string | null;
    scraped_at: string | null;
    confidence: number;
    source_type: string;
  }>;
  generated_at: string;
}

interface ForagerResultsDialogProps {
  foragerId: string | null;
  sourceName?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

async function downloadBlob(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function shortForagerId(id: string): string {
  return `F-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

/** Operator harvest report — readable findings + PDF/Markdown export. */
export function ForagerResultsDialog({
  foragerId,
  sourceName,
  open,
  onOpenChange,
}: ForagerResultsDialogProps): JSX.Element | null {
  const [report, setReport] = useState<ForagerHarvestReportRow | null>(null);
  const [structuredRows, setStructuredRows] = useState<
    Array<{ knowledge_id: string; row: Record<string, string | null> }>
  >([]);
  const [extractSchema, setExtractSchema] = useState<string | null>(null);
  const [exportDestination, setExportDestination] = useState<"csv" | "notion" | "sheet">("csv");
  const [notionDatabaseId, setNotionDatabaseId] = useState("");
  const [loading, setLoading] = useState(false);
  const [exportBusy, setExportBusy] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const onOpenChangeRef = useRef(onOpenChange);
  onOpenChangeRef.current = onOpenChange;

  const loadReport = useCallback(async (targetId: string) => {
    setLoading(true);
    setReport(null);
    try {
      const body = await hiveGet<ForagerHarvestReportRow>(
        `foragers/${encodeURIComponent(targetId)}/report?item_limit=25`,
      );
      setReport(body);
      try {
        const structured = await hiveGet<{
          extract_schema: string;
          rows: Array<{ knowledge_id: string; row: Record<string, string | null> }>;
        }>(`foragers/${encodeURIComponent(targetId)}/structured-rows?limit=25`);
        setExtractSchema(structured.extract_schema);
        setStructuredRows(structured.rows ?? []);
      } catch {
        setExtractSchema(null);
        setStructuredRows([]);
      }
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Forager report unavailable");
      onOpenChangeRef.current(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open || !foragerId) {
      setReport(null);
      setStructuredRows([]);
      setExtractSchema(null);
      setLoading(false);
      return;
    }
    void loadReport(foragerId);
  }, [open, foragerId, loadReport]);

  async function approveStructuredForExport(): Promise<void> {
    if (!foragerId || !structuredRows.length) return;
    setExportBusy("approve");
    try {
      const res = await hivePostJson<{ ok: boolean; tagged: number }>(
        `foragers/${encodeURIComponent(foragerId)}/export-lane/approve`,
        { knowledge_ids: structuredRows.map((row) => row.knowledge_id) },
      );
      toast.success(`Approved ${res.tagged} row(s) for export`);
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Approve failed");
    } finally {
      setExportBusy(null);
    }
  }

  async function runExportLane(): Promise<void> {
    if (!foragerId) return;
    setExportBusy("export");
    try {
      const res = await hivePostJson<{
        ok: boolean;
        message: string;
        csv_content?: string | null;
        row_count: number;
        simulated: boolean;
      }>(`foragers/${encodeURIComponent(foragerId)}/export-lane/submit`, {
        destination: exportDestination,
        mode: "simulate",
        approved_only: true,
        knowledge_ids: structuredRows.map((row) => row.knowledge_id),
        notion_database_id: notionDatabaseId.trim() || null,
        operator_confirmed: false,
      });
      if (res.csv_content && (exportDestination === "csv" || exportDestination === "sheet")) {
        const blob = new Blob([res.csv_content], { type: "text/csv;charset=utf-8" });
        await downloadBlob(blob, `forager-export-${foragerId.slice(0, 8)}.csv`);
      }
      toast.success(res.message || `Exported ${res.row_count} row(s)`);
    } catch (err) {
      toast.error(err instanceof HiveApiError ? err.message : "Export failed");
    } finally {
      setExportBusy(null);
    }
  }

  async function exportReport(format: "html" | "markdown" | "pdf"): Promise<void> {
    if (!foragerId) {
      return;
    }
    setExportBusy(format);
    try {
      const res = await fetch(
        `/api/proxy/foragers/${encodeURIComponent(foragerId)}/report/export?format=${format}`,
        { cache: "no-store" },
      );
      if (!res.ok) {
        throw new Error("Report export failed");
      }
      const blob = await res.blob();
      const tail = foragerId.replace(/-/g, "").slice(-8).toUpperCase();
      const ext = format === "markdown" ? "md" : format === "pdf" ? "pdf" : "html";
      await downloadBlob(blob, `forager-${tail}-report.${ext}`);
      toast.success(`Report downloaded (${format.toUpperCase()})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report export failed");
    } finally {
      setExportBusy(null);
    }
  }

  if (!open || !foragerId) {
    return null;
  }

  const knowledgeHref = foragerKnowledgeHref({
    foragerId,
    searchQuery: sourceName ?? report?.name,
  });

  return (
    <HiveModalShell
      open
      onClose={() => onOpenChange(false)}
      labelledBy="forager-results-title"
      align="center"
      zIndexClass="z-[72]"
      closeLabel="Close forager report"
      panelClassName="qs-bubble flex max-h-[min(92dvh,920px)] w-full max-w-3xl flex-col overflow-hidden rounded-(--qs-radius-lg)"
    >
      <header className="flex shrink-0 items-start justify-between gap-3 border-b border-(--qs-border) px-4 py-4 sm:px-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <FileText className="h-4 w-4 shrink-0 text-pollen" aria-hidden />
            <h2 id="forager-results-title" className="text-lg font-semibold text-(--qs-text)">
              Forager results
            </h2>
            {report ? (
              <>
                <V4Badge tone="gold">{shortForagerId(report.forager_id)}</V4Badge>
                <V4Badge tone="purple">{report.source_type}</V4Badge>
                <V4Badge tone="info">{report.items_total} signals</V4Badge>
              </>
            ) : null}
          </div>
          {report ? (
            <p className="hive-readable-prose mt-1 line-clamp-2 text-sm text-(--qs-text-2)" title={report.name}>
              {report.name}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--icon shrink-0"
          aria-label="Close"
          onClick={() => onOpenChange(false)}
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </header>

      <div ref={scrollRef} className={hiveModalScrollBodyClass}>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-5 w-5 animate-spin text-pollen" aria-hidden />
            Loading harvest report…
          </div>
        ) : report ? (
          <div className="hive-readable-prose space-y-5">
            <section>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-pollen">Executive summary</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-(--qs-text)">
                {report.executive_summary}
              </p>
            </section>

            {structuredRows.length > 0 ? (
              <section data-testid="forager-structured-rows">
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-cyan">
                  Structured extract
                  {extractSchema ? (
                    <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                      schema: {extractSchema}
                    </span>
                  ) : null}
                </p>
                <div className="mt-3 overflow-x-auto rounded-xl border border-cyan/25 bg-black/20">
                  <table className="min-w-full text-left text-xs">
                    <thead className="border-b border-white/10 text-(--qs-text-3)">
                      <tr>
                        {Object.keys(structuredRows[0]?.row ?? {}).map((key) => (
                          <th key={key} className="px-3 py-2 font-medium">{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {structuredRows.map((entry) => (
                        <tr key={entry.knowledge_id} className="border-b border-white/5 last:border-0">
                          {Object.entries(entry.row).map(([key, value]) => (
                            <td key={key} className="max-w-[200px] truncate px-3 py-2 text-(--qs-text-2)">
                              {value ?? "—"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-white/10 pt-3">
                  <label className="flex min-w-[120px] flex-col gap-1 text-xs">
                    <span className="text-(--qs-text-3)">Destination</span>
                    <select
                      className="qs-input"
                      value={exportDestination}
                      onChange={(e) => setExportDestination(e.target.value as "csv" | "notion" | "sheet")}
                    >
                      <option value="csv">CSV download</option>
                      <option value="sheet">Google Sheet (CSV)</option>
                      <option value="notion">Notion DB (simulate)</option>
                    </select>
                  </label>
                  {exportDestination === "notion" ? (
                    <label className="flex min-w-[180px] flex-1 flex-col gap-1 text-xs">
                      <span className="text-(--qs-text-3)">Notion database ID</span>
                      <input
                        className="qs-input"
                        placeholder="Optional — simulate payload"
                        value={notionDatabaseId}
                        onChange={(e) => setNotionDatabaseId(e.target.value)}
                      />
                    </label>
                  ) : null}
                  <button
                    type="button"
                    className="qs-btn qs-btn--ghost qs-btn--sm"
                    disabled={Boolean(exportBusy) || !structuredRows.length}
                    onClick={() => void approveStructuredForExport()}
                  >
                    Approve for export
                  </button>
                  <button
                    type="button"
                    className="qs-btn qs-btn--primary qs-btn--sm"
                    disabled={Boolean(exportBusy) || !structuredRows.length}
                    onClick={() => void runExportLane()}
                    data-testid="forager-export-lane-submit"
                  >
                    Export {structuredRows.length} row{structuredRows.length === 1 ? "" : "s"}
                  </button>
                </div>
              </section>
            ) : null}

            <section>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
                Key findings
                {report.items.length > 0 ? (
                  <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                    (showing {report.items.length} of {report.items_total})
                  </span>
                ) : null}
              </p>
              {report.items.length === 0 ? (
                <div className="mt-3 space-y-3 rounded-xl border border-dashed border-pollen/35 bg-black/20 px-4 py-5 text-sm text-(--qs-text-3) sm:px-5">
                  <p>No harvested signals yet for this forager.</p>
                  <ol className="list-decimal space-y-1 pl-5 text-xs text-(--qs-text-2)">
                    <li>Open <strong>Foragers</strong> → find this row → click <strong>Run</strong> (RSS feeds scrape on Run).</li>
                    <li>In <strong>Edit</strong>, verify <code className="text-pollen">source_config.feeds</code> has working RSS URLs.</li>
                    <li>Wait ~30s, reopen <strong>Results</strong>, then export PDF again.</li>
                  </ol>
                </div>
              ) : (
                <ul className="mt-3 space-y-3">
                  {report.items.map((item, index) => (
                    <li
                      key={`${item.title}-${index}`}
                      className="hive-readable-card rounded-xl border border-pollen/30 bg-black/25 px-4 py-3.5 sm:px-5 sm:py-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
                        <p className="min-w-0 flex-1 text-sm font-medium leading-snug text-(--qs-text)">
                          {item.title}
                        </p>
                        <span className="shrink-0 text-[10px] leading-relaxed text-(--qs-text-4)">
                          {item.scraped_at ? formatTimeAgoIso(item.scraped_at) : "—"}
                          {" · "}
                          {Math.round(item.confidence * 100)}% conf.
                        </span>
                      </div>
                      <p className="mt-2.5 whitespace-pre-wrap text-xs leading-relaxed text-(--qs-text-2)">
                        {item.body.length > 1200 ? `${item.body.slice(0, 1197)}…` : item.body}
                      </p>
                      {item.source_url ? (
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="hive-readable-link mt-2.5 text-xs text-cyan hover:underline"
                        >
                          {item.source_url}
                        </a>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        ) : null}
      </div>

      <footer className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-(--qs-border) px-4 py-3 sm:px-5">
        <Link href={knowledgeHref} className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5">
          <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          Raw HiveMind data
        </Link>
        <div className="flex flex-wrap gap-2">
          {(["pdf", "markdown", "html"] as const).map((format) => (
            <button
              key={format}
              type="button"
              className={cn(
                "qs-btn qs-btn--ghost qs-btn--sm gap-1.5",
                format === "pdf" && "qs-btn--primary",
                exportBusy === format && "opacity-60",
              )}
              disabled={Boolean(exportBusy) || loading || !report}
              onClick={() => void exportReport(format)}
            >
              {exportBusy === format ? (
                <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
              ) : (
                <Download className="h-3.5 w-3.5" aria-hidden />
              )}
              {format.toUpperCase()}
            </button>
          ))}
        </div>
      </footer>
    </HiveModalShell>
  );
}
