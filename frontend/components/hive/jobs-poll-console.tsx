"use client";

import { Loader2Icon, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { HiveApiError, hiveGet } from "@/lib/api";
import type { HiveAsyncJobStatusPayload } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

/** Poll ``GET /jobs/{celery_task_id}`` — async swarm workflow telemetry. */
export function JobsPollConsole() {
  const [taskId, setTaskId] = useState("");
  const [manualBusy, setManualBusy] = useState(false);
  const [pollPulse, setPollPulse] = useState(false);
  const [auto, setAuto] = useState(false);
  const [snapshot, setSnapshot] = useState<HiveAsyncJobStatusPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const pollOnce = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent ?? false;
    const id = taskId.trim();
    if (!id) {
      setErr("Enter a Celery task id.");
      return;
    }
    if (silent) {
      setPollPulse(true);
    } else {
      setManualBusy(true);
    }
    setErr(null);
    try {
      const row = await hiveGet<HiveAsyncJobStatusPayload>(`jobs/${encodeURIComponent(id)}`);
      setSnapshot(row);
    } catch (e) {
      setSnapshot(null);
      setErr(e instanceof HiveApiError ? e.message : "Poll failed.");
    } finally {
      if (silent) {
        setPollPulse(false);
      } else {
        setManualBusy(false);
      }
    }
  }, [taskId]);

  useEffect(() => {
    if (!auto) {
      return undefined;
    }
    const t = window.setInterval(() => {
      void pollOnce({ silent: true });
    }, 4000);
    return () => window.clearInterval(t);
  }, [auto, pollOnce]);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-10 text-zinc-200">
      <header className="space-y-2">
        <p className="font-[family-name:var(--font-poppins)] text-xs uppercase tracking-[0.42em] text-cyan">Phase 2.6 · Ops</p>
        <h1 className="font-[family-name:var(--font-poppins)] text-3xl font-bold text-pollen md:text-[2rem]">Async workflow jobs</h1>
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-400">
          Paste a Celery task id from queued swarm workflows — single-flight polling keeps ~16 GB hosts predictable (pause auto-refresh when
          idle).
        </p>
      </header>

      <section className="rounded-[26px] border border-[#1c2045] bg-black/72 p-5 md:p-6">
        {(manualBusy || pollPulse) && !err ? (
          <p className="mb-3 font-[family-name:var(--font-poppins)] text-xs text-cyan/85" aria-live="polite">
            {manualBusy ? "Fetching job snapshot…" : "Background poll updating snapshot…"}
          </p>
        ) : null}
        <label className="flex flex-col gap-2 font-[family-name:var(--font-poppins)] text-sm font-medium text-[#BEBED6]">
          Celery task id
          <input
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            placeholder="e.g. celery-task-uuid"
            className="min-h-[44px] rounded-xl border border-[#1e2348] bg-black/76 px-3 py-3 font-mono text-sm text-[#EEEEFF]"
          />
        </label>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={manualBusy}
            onClick={() => void pollOnce()}
            className={cn(
              "inline-flex min-h-[44px] items-center gap-2 rounded-2xl border border-pollen/70 px-6 py-3 font-[family-name:var(--font-poppins)] text-sm font-semibold text-pollen hover:bg-pollen/10 disabled:opacity-40 touch-manipulation",
            )}
          >
            {manualBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
            Poll now
          </button>
          <label className="flex min-h-[44px] items-center gap-2 rounded-2xl border border-cyan/30 px-4 py-3 font-[family-name:var(--font-poppins)] text-xs text-cyan touch-manipulation">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="accent-cyan" />
            Auto every 4s
          </label>
        </div>

        {err ? (
          <p className="mt-4 rounded-xl border border-danger/35 bg-black/65 px-3 py-2 text-sm text-danger" role="alert">
            {err}
          </p>
        ) : null}

        {snapshot ? (
          <pre className="mt-6 max-h-[min(420px,55vh)] overflow-auto rounded-2xl border border-[#252a55] bg-black/85 p-4 font-mono text-[11px] leading-relaxed text-[#B7F6FF] hive-scrollbar">
            {JSON.stringify(snapshot, null, 2)}
          </pre>
        ) : (
          <p className="mt-6 font-[family-name:var(--font-poppins)] text-sm text-zinc-500">No snapshot yet.</p>
        )}
      </section>
    </main>
  );
}
