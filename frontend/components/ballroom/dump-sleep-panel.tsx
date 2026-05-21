"use client";

import { Loader2Icon, MoonStar, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { OvernightVoiceReportPlayer } from "@/components/hive/overnight-voice-report-player";
import { HiveApiError, hiveGet } from "@/lib/api";
import { usePlatform } from "@/components/hive/platform-context";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";

interface DumpSleepBatchResponse {
  id: string;
  status: string;
  file_count: number;
  items_ingested: number;
  stalled_signals: number;
  pollen_earned: number;
  briefing_md: string;
  voice_note_present: boolean;
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

/** Ballroom entry — upload folder dump before sleep, queue overnight swarm processing. */
export function DumpSleepPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [voiceNote, setVoiceNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [activeBatch, setActiveBatch] = useState<DumpSleepBatchResponse | null>(null);

  const pollBatch = useCallback(async (batchId: string) => {
    try {
      const row = await hiveGet<DumpSleepBatchResponse>(`dump-sleep/batches/${batchId}`);
      setActiveBatch(row);
      if (row.status === "completed") {
        setHint("Overnight report ready — check Dashboard Memory card.");
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
    if ((!files || files.length === 0) && !voiceNote.trim()) {
      setHint("Add text/markdown files or a voice note transcript.");
      return;
    }
    setBusy(true);
    setHint(null);
    try {
      const fd = new FormData();
      if (files) {
        for (const file of Array.from(files)) {
          fd.append("files", file);
        }
      }
      if (voiceNote.trim()) {
        fd.append("voice_note", voiceNote.trim());
      }
      const res = await fetch("/api/proxy/dump-sleep/batches", {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      const text = await res.text();
      if (!res.ok) {
        setHint(`Upload failed (${String(res.status)}): ${text.slice(0, 240)}`);
        return;
      }
      const batch = JSON.parse(text) as DumpSleepBatchResponse;
      setActiveBatch(batch);
      setVoiceNote("");
      if (inputRef.current) {
        inputRef.current.value = "";
      }
      setHint("Queued for overnight processing — pollination bees at work.");
    } catch (e) {
      setHint(e instanceof Error ? e.message : "upload_failed");
    } finally {
      setBusy(false);
    }
  }, [voiceNote]);

  if (!hasFeature("dump_sleep")) {
    return null;
  }

  return (
    <V4Card className="v4-card-interactive border-pollen/30">
      <V4CardHeader
        title="Dump & Sleep"
        description="Drop folder notes before bed — wake up to a verified morning briefing."
        actions={
          activeBatch ? (
            <V4Badge tone={statusTone(activeBatch.status)}>{activeBatch.status}</V4Badge>
          ) : (
            <MoonStar className="h-4 w-4 text-pollen" aria-hidden />
          )
        }
      />

      <div className="space-y-3">
        <label className="flex cursor-pointer flex-col gap-2 rounded-xl border border-dashed border-pollen/40 bg-black/25 p-4 text-sm text-(--qs-text-2)">
          <span className="inline-flex items-center gap-2 font-medium text-pollen">
            <Upload className="h-4 w-4" aria-hidden />
            Folder dump (.txt, .md, .json, .csv)
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".txt,.md,.markdown,.json,.csv,.py,.html,.xml,.yaml,.yml,.log"
            className="text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-pollen/20 file:px-3 file:py-1.5 file:text-pollen"
          />
        </label>

        <textarea
          value={voiceNote}
          onChange={(e) => setVoiceNote(e.target.value)}
          rows={2}
          placeholder="Optional voice note transcript…"
          className="w-full rounded-xl border border-(--qs-border) bg-black/30 px-3 py-2 text-sm text-(--qs-text-1) placeholder:text-(--qs-text-3)"
        />

        <button
          type="button"
          disabled={busy}
          onClick={() => void onSubmit()}
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-2"
        >
          {busy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Queue overnight swarm
        </button>

        {hint ? <p className="text-xs text-(--qs-text-2)">{hint}</p> : null}

        {activeBatch?.status === "completed" ? (
          <div className="rounded-xl border border-(--qs-border) bg-black/25 p-3 text-xs text-(--qs-text-2)">
            <OvernightVoiceReportPlayer enabled className="mb-3" />
            <p>
              ingested={activeBatch.items_ingested} · stalled=
              <span className="text-magenta">{activeBatch.stalled_signals}</span> · pollen=
              <span className="text-pollen">{activeBatch.pollen_earned.toFixed(1)}</span>
            </p>
            {activeBatch.briefing_md ? (
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-(--qs-text-3)">
                {activeBatch.briefing_md.slice(0, 1200)}
              </pre>
            ) : null}
          </div>
        ) : null}
      </div>
    </V4Card>
  );
}
