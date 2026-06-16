"use client";

import { DownloadIcon, FileJsonIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hiveFetchRaw } from "@/lib/api";

interface VerifiedDatasetSnapshot {
  enabled: boolean;
  min_score: number;
  min_score_label: string;
  deliverable_candidates: number;
  recipe_candidates: number;
  exportable_rows: number;
  max_rows: number;
  operator_hint: string;
}

interface VerifiedDatasetRow {
  instruction: string;
  input: string;
  output: string;
  source_type: "deliverable" | "recipe";
  source_id: string;
  source_label: string;
  critic_score: number | null;
}

interface VerifiedDatasetPreview {
  ok: boolean;
  total_rows: number;
  sample_rows: VerifiedDatasetRow[];
  message: string;
}

/** Settings panel — verified Alpaca JSONL export (Track M LOC5). */
export function VerifiedDatasetExportPanel(): JSX.Element | null {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [snapshot, setSnapshot] = useState<VerifiedDatasetSnapshot | null>(null);
  const [preview, setPreview] = useState<VerifiedDatasetPreview | null>(null);
  const [disabled, setDisabled] = useState(false);

  const load = useCallback(async () => {
    try {
      const [snap, prev] = await Promise.all([
        hiveGet<VerifiedDatasetSnapshot>("llm-routing/verified-dataset"),
        hiveGet<VerifiedDatasetPreview>("llm-routing/verified-dataset/preview?sample_limit=3"),
      ]);
      setSnapshot(snap);
      setPreview(prev);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Verified dataset export unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const download = useCallback(async () => {
    setExporting(true);
    try {
      const res = await hiveFetchRaw("llm-routing/verified-dataset/export");
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail =
          typeof body === "object" && body !== null && "detail" in body
            ? String((body as { detail: unknown }).detail)
            : res.statusText;
        throw new HiveApiError(detail || "Export failed.", res.status, body);
      }
      const blob = await res.blob();
      const disposition = res.headers.get("content-disposition") ?? "";
      const match = /filename="([^"]+)"/.exec(disposition);
      const filename = match?.[1] ?? "queenswarm-verified-dataset.jsonl";
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Verified dataset JSONL downloaded.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }, []);

  if (disabled) {
    return null;
  }

  return (
    <div data-testid="verified-dataset-export-panel">
      <V4Card className="v4-card-interactive border-cyan/25">
        <V4CardHeader
          title="Verified dataset export · Alpaca JSONL"
          description="Critic-approved deliverables + verified recipes for Unsloth fine-tune (LOC5)."
          actions={
            snapshot ? (
              <V4Badge tone={snapshot.exportable_rows > 0 ? "ok" : "info"}>
                {snapshot.exportable_rows} row{snapshot.exportable_rows === 1 ? "" : "s"}
              </V4Badge>
            ) : (
              <FileJsonIcon className="h-4 w-4 text-cyan" aria-hidden />
            )
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading export lane…
          </p>
        ) : null}

        {snapshot ? (
          <div className="space-y-4">
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-(--qs-text-3)">Min critic score</dt>
                <dd className="font-mono text-xs text-pollen">{snapshot.min_score_label}</dd>
              </div>
              <div>
                <dt className="text-(--qs-text-3)">Deliverables</dt>
                <dd className="font-mono text-xs text-cyan">{snapshot.deliverable_candidates}</dd>
              </div>
              <div>
                <dt className="text-(--qs-text-3)">Verified recipes</dt>
                <dd className="font-mono text-xs text-cyan">{snapshot.recipe_candidates}</dd>
              </div>
              <div>
                <dt className="text-(--qs-text-3)">Max rows</dt>
                <dd className="font-mono text-xs">{snapshot.max_rows}</dd>
              </div>
            </dl>

            {preview?.message ? (
              <p className="text-xs text-(--qs-text-3)">{preview.message}</p>
            ) : null}

            {preview && preview.sample_rows.length > 0 ? (
              <ul className="space-y-2 text-xs">
                {preview.sample_rows.map((row) => (
                  <li
                    key={`${row.source_type}-${row.source_id}`}
                    className="rounded-md border border-cyan/20 bg-cyan/5 px-3 py-2"
                  >
                    <span className="font-medium text-cyan">{row.source_label || row.source_type}</span>
                    <span className="ml-2 text-(--qs-text-3)">
                      {row.source_type}
                      {row.critic_score != null ? ` · ${(row.critic_score * 5).toFixed(1)}/5` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}

            <button
              type="button"
              disabled={exporting || snapshot.exportable_rows === 0}
              onClick={() => void download()}
              className="inline-flex items-center gap-2 rounded-md border border-cyan/40 px-3 py-2 text-sm text-cyan hover:bg-cyan/10 disabled:opacity-50"
            >
              {exporting ? (
                <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <DownloadIcon className="h-4 w-4" aria-hidden />
              )}
              Download JSONL
            </button>

            <p className="text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
          </div>
        ) : null}
      </V4Card>
    </div>
  );
}
