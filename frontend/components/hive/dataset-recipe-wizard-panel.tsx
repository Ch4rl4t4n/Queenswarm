"use client";

import { BookOpenIcon, DownloadIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveFetchRaw, hiveGet, hivePostJson } from "@/lib/api";

interface DatasetRecipePair {
  instruction: string;
  input: string;
  output: string;
  approved: boolean;
}

interface DatasetRecipeSnapshot {
  enabled: boolean;
  local_only: boolean;
  local_model_slug: string;
  status: string;
  source_filename: string | null;
  chunk_count: number;
  draft_pair_count: number;
  approved_pair_count: number;
  draft_pairs: DatasetRecipePair[];
  operator_hint: string;
}

/** Settings panel — PDF/CSV → Q&A via local model (Track M LOC6). */
export function DatasetRecipeWizardPanel(): JSX.Element | null {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<DatasetRecipeSnapshot | null>(null);
  const [disabled, setDisabled] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await hiveGet<DatasetRecipeSnapshot>("llm-routing/dataset-recipe");
      setSnapshot(body);
      setDisabled(false);
    } catch (e) {
      if (e instanceof HiveApiError && e.status === 404) {
        setDisabled(true);
      } else {
        toast.error(e instanceof HiveApiError ? e.message : "Dataset recipe wizard unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const parseFile = useCallback(async () => {
    const file = inputRef.current?.files?.[0];
    if (!file) {
      toast.error("Choose a CSV, PDF, or text file.");
      return;
    }
    setBusy("parse");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/proxy/llm-routing/dataset-recipe/parse", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail =
          typeof body === "object" && body !== null && "detail" in body
            ? String((body as { detail: unknown }).detail)
            : res.statusText;
        throw new HiveApiError(detail, res.status, body);
      }
      toast.success(String((body as { message?: string }).message || "Document parsed."));
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Parse failed.");
    } finally {
      setBusy(null);
    }
  }, [load]);

  const generate = useCallback(async () => {
    setBusy("generate");
    try {
      const body = await hivePostJson<{ message?: string }>("llm-routing/dataset-recipe/generate", {});
      toast.success(body.message || "Draft Q&A generated.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Generate failed.");
    } finally {
      setBusy(null);
    }
  }, [load]);

  const approveAll = useCallback(async () => {
    setBusy("approve");
    try {
      const indices = (snapshot?.draft_pairs ?? []).map((_, idx) => idx);
      await hivePostJson("llm-routing/dataset-recipe/approve", { approved_indices: indices });
      toast.success("Draft pairs approved.");
      await load();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Approve failed.");
    } finally {
      setBusy(null);
    }
  }, [load, snapshot?.draft_pairs]);

  const download = useCallback(async () => {
    setBusy("export");
    try {
      const res = await hiveFetchRaw("llm-routing/dataset-recipe/export");
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new HiveApiError(String((body as { detail?: string }).detail || res.statusText), res.status, body);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "queenswarm-dataset-recipe.jsonl";
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Dataset recipe JSONL downloaded.");
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Export failed.");
    } finally {
      setBusy(null);
    }
  }, []);

  if (disabled) {
    return null;
  }

  return (
    <div data-testid="dataset-recipe-wizard-panel">
      <V4Card className="v4-card-interactive border-magenta/25">
        <V4CardHeader
          title="Dataset Recipe wizard · local Q&A"
          description="PDF/CSV → Alpaca pairs via local model only — approve before export (LOC6)."
          actions={
            snapshot ? (
              <V4Badge tone={snapshot.approved_pair_count > 0 ? "ok" : "info"}>
                {snapshot.draft_pair_count} draft
              </V4Badge>
            ) : (
              <BookOpenIcon className="h-4 w-4 text-magenta" aria-hidden />
            )
          }
        />

        {loading ? (
          <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading wizard…
          </p>
        ) : null}

        {snapshot ? (
          <div className="space-y-4">
            <p className="text-xs text-(--qs-text-3)">
              Model: <span className="font-mono text-pollen">{snapshot.local_model_slug}</span>
              {snapshot.local_only ? " · local-only" : ""}
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".csv,.pdf,.txt,.md,text/csv,application/pdf"
              className="block w-full text-sm text-(--qs-text-3)"
            />
            <button
              type="button"
              disabled={busy === "parse"}
              onClick={() => void parseFile()}
              className="rounded-md border border-magenta/40 px-3 py-2 text-sm text-magenta hover:bg-magenta/10 disabled:opacity-50"
            >
              Parse upload
            </button>

            {snapshot.draft_pairs.length > 0 ? (
              <ul className="space-y-2 text-xs">
                {snapshot.draft_pairs.slice(0, 3).map((row, idx) => (
                  <li key={`${row.input.slice(0, 24)}-${idx}`} className="rounded-md border border-magenta/20 px-3 py-2">
                    <span className="font-medium text-magenta">{row.input.slice(0, 80)}</span>
                    <span className="ml-2 text-(--qs-text-3)">{row.approved ? "approved" : "draft"}</span>
                  </li>
                ))}
              </ul>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy === "generate"}
                onClick={() => void generate()}
                className="inline-flex items-center gap-2 rounded-md border border-cyan/40 px-3 py-2 text-sm text-cyan"
              >
                {busy === "generate" ? <Loader2Icon className="h-4 w-4 animate-spin" /> : <SparklesIcon className="h-4 w-4" />}
                Generate Q&A
              </button>
              <button
                type="button"
                disabled={busy === "approve" || snapshot.draft_pair_count === 0}
                onClick={() => void approveAll()}
                className="rounded-md border border-success/40 px-3 py-2 text-sm text-success disabled:opacity-50"
              >
                Approve all
              </button>
              <button
                type="button"
                disabled={busy === "export" || snapshot.approved_pair_count === 0}
                onClick={() => void download()}
                className="inline-flex items-center gap-2 rounded-md border border-pollen/40 px-3 py-2 text-sm text-pollen disabled:opacity-50"
              >
                {busy === "export" ? <Loader2Icon className="h-4 w-4 animate-spin" /> : <DownloadIcon className="h-4 w-4" />}
                Export JSONL
              </button>
            </div>

            <p className="text-xs text-(--qs-text-3)">{snapshot.operator_hint}</p>
          </div>
        ) : null}
      </V4Card>
    </div>
  );
}
