"use client";

import { Loader2Icon, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

interface GraphifyBatchResponse {
  id: string;
  status: string;
  folder_label: string;
  file_count: number;
  items_ingested: number;
  graph_nodes_created: number;
  vectors_embedded: number;
  pollen_earned: number;
  summary_md: string;
  vault_rel_path?: string | null;
  created_at: string;
  processed_at: string | null;
  error_text?: string | null;
}

function statusTone(status: string): "ok" | "warn" | "err" | "info" {
  const s = status.toLowerCase();
  if (s.includes("complete")) return "ok";
  if (s.includes("fail")) return "err";
  if (s.includes("process") || s.includes("queue")) return "info";
  return "warn";
}

/** Knowledge hub entry — upload folder notes for vault mirror + Neo4j graph ingest. */
export function AutoGraphifyPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [folderLabel, setFolderLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [activeBatch, setActiveBatch] = useState<GraphifyBatchResponse | null>(null);

  const pollBatch = useCallback(async (batchId: string) => {
    try {
      const row = await hiveGet<GraphifyBatchResponse>(`auto-graphify/batches/${batchId}`);
      setActiveBatch(row);
      if (row.status === "completed") {
        setHint("Graph ingest complete — explore nodes in HiveMind below.");
      } else if (row.status === "failed") {
        setHint(row.error_text ?? "Batch failed.");
      }
    } catch (e) {
      setHint(e instanceof HiveApiError ? e.message : "Could not load batch status.");
    }
  }, []);

  useIntervalWhenVisible(
    () => {
      if (!activeBatch?.id) return;
      if (activeBatch.status === "queued" || activeBatch.status === "processing") {
        void pollBatch(activeBatch.id);
      }
    },
    4000,
    { enabled: Boolean(activeBatch?.id) },
  );

  const onSubmit = useCallback(async () => {
    const files = inputRef.current?.files;
    if (!files || files.length === 0) {
      setHint("Select `.md` / `.txt` files from a project folder.");
      return;
    }
    setBusy(true);
    setHint(null);
    try {
      const fd = new FormData();
      for (const file of Array.from(files)) {
        fd.append("files", file, file.webkitRelativePath || file.name);
      }
      if (folderLabel.trim()) {
        fd.append("folder_label", folderLabel.trim());
      }
      const res = await fetch("/api/proxy/auto-graphify/batches", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      const text = await res.text();
      if (!res.ok) {
        setHint(`Upload failed (${String(res.status)}): ${text.slice(0, 240)}`);
        return;
      }
      const row = JSON.parse(text) as GraphifyBatchResponse;
      setActiveBatch(row);
      setHint("Batch queued — vault mirror + graph nodes processing.");
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (e) {
      setHint(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }, [folderLabel]);

  if (!hasFeature("auto_graphify")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-cyan/25">
      <V4CardHeader
        title="Auto-Graphify"
        description="Upload a project folder — mirror to vault, embed vectors, and create Neo4j document nodes."
      />

      <div className="space-y-4">
        <label className="block space-y-2 text-sm">
          <span className="text-(--qs-text-2)">Folder label</span>
          <input
            type="text"
            value={folderLabel}
            onChange={(e) => setFolderLabel(e.target.value)}
            placeholder="e.g. Product research Q2"
            className="qs-input w-full"
            disabled={busy}
          />
        </label>

        <label className="block space-y-2 text-sm">
          <span className="text-(--qs-text-2)">Files (.md, .txt, .json…)</span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".md,.txt,.markdown,.json,.csv,.yaml,.yml,.py,.html,.xml,.log"
            className="block w-full text-sm text-(--qs-text-2) file:mr-3 file:rounded-lg file:border-0 file:bg-pollen/15 file:px-3 file:py-2 file:text-xs file:uppercase file:text-pollen"
            disabled={busy}
          />
        </label>

        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-2"
          disabled={busy}
          onClick={() => void onSubmit()}
        >
          {busy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
          Queue graphify
        </button>

        {hint ? <p className="text-sm text-(--qs-text-3)">{hint}</p> : null}

        {activeBatch ? (
          <div className="space-y-2 rounded-xl border border-(--qs-border) bg-(--qs-surface-2)/40 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <V4Badge tone={statusTone(activeBatch.status)}>{activeBatch.status}</V4Badge>
              <V4Badge tone="info">{activeBatch.items_ingested} docs</V4Badge>
              <V4Badge tone="ok">{activeBatch.graph_nodes_created} nodes</V4Badge>
              <V4Badge tone="warn">{activeBatch.pollen_earned.toFixed(1)} pollen</V4Badge>
            </div>
            {activeBatch.summary_md ? (
              <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs text-(--qs-text-2)">
                {activeBatch.summary_md}
              </pre>
            ) : null}
          </div>
        ) : null}
      </div>
    </V4Card>
  );
}
