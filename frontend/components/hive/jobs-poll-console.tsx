"use client";

import { Loader2Icon, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { V4Card } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { COCKPIT_POLL_JOBS_MS } from "@/lib/cockpit-poll-profile";
import {
  EXECUTION_LANE_CROSS_LINK_LABELS,
  TASKS_HUB_PATH,
  WORKFLOWS_PATH,
} from "@/lib/execution-lane-routes";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { HiveAsyncJobStatusPayload } from "@/lib/hive-types";

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

  useIntervalWhenVisible(
    () => {
      void pollOnce({ silent: true });
    },
    auto ? COCKPIT_POLL_JOBS_MS : null,
    { runImmediately: auto },
  );

  return (
    <HivePageShell
      title="Async workflow jobs"
      subtitle="Phase 2.6 · Ops — paste a Celery task id from queued swarm workflows. Single-flight polling keeps ~16 GB hosts predictable (pause auto-refresh when idle)."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link href={TASKS_HUB_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {EXECUTION_LANE_CROSS_LINK_LABELS.toTasksHub}
          </Link>
          <Link href={WORKFLOWS_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows}
          </Link>
        </div>
      }
    >
      <V4Card>
        {(manualBusy || pollPulse) && !err ? (
          <p className="mb-3 text-xs text-(--qs-cyan)" aria-live="polite">
            {manualBusy ? "Fetching job snapshot…" : "Background poll updating snapshot…"}
          </p>
        ) : null}
        <label className="flex flex-col gap-2 text-sm font-medium text-(--qs-text-2)">
          Celery task id
          <input
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            placeholder="e.g. celery-task-uuid"
            className="qs-input font-mono"
          />
        </label>

        <div className="v4-jobs-actions mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={manualBusy}
            onClick={() => void pollOnce()}
            className="qs-btn qs-btn--primary qs-btn--sm w-full gap-2 disabled:opacity-40 sm:w-auto"
          >
            {manualBusy ? <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
            Poll now
          </button>
          <label className="qs-btn qs-btn--ghost qs-btn--sm flex min-h-[36px] w-full cursor-pointer items-center justify-center gap-2 sm:w-auto">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="accent-(--qs-cyan)" />
            Auto every 4s
          </label>
        </div>

        {err ? (
          <p className="mt-4 rounded-xl border border-(--qs-red)/35 bg-black/65 px-3 py-2 text-sm text-(--qs-red)" role="alert">
            {err}
          </p>
        ) : null}

        {snapshot ? (
          <pre className="mt-6 max-h-[min(420px,55vh)] overflow-auto rounded-2xl border border-(--qs-border) bg-black/85 p-4 font-mono text-[11px] leading-relaxed text-(--qs-cyan) hive-scrollbar">
            {JSON.stringify(snapshot, null, 2)}
          </pre>
        ) : (
          <p className="mt-6 text-sm text-(--qs-text-3)">No snapshot yet.</p>
        )}
      </V4Card>
    </HivePageShell>
  );
}
