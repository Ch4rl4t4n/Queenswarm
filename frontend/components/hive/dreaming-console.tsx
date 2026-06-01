"use client";

import { Loader2Icon, Moon, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { InfoHint } from "@/components/hive/info-hint";
import { DreamReportsGrid, DreamReportsGridSkeleton } from "@/components/hive/dream-reports-grid";
import type { DreamCycleRow } from "@/components/hive/dream-report-info-dialog";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DreamingSettingsResponse {
  enabled: boolean;
  frequency_hours: number;
  routine_id: string | null;
}

interface RunNowResponse {
  status: string;
  celery_task_id: string;
}

/** Tenant-scoped dreaming controls — Hive Control V4. */
export function DreamingConsole(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [settings, setSettings] = useState<DreamingSettingsResponse | null>(null);
  const [cycles, setCycles] = useState<DreamCycleRow[]>([]);
  const [frequencyHours, setFrequencyHours] = useState(24);
  const [lastRunTaskId, setLastRunTaskId] = useState<string | null>(null);
  const [clearBusy, setClearBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, rows] = await Promise.all([
        hiveGet<DreamingSettingsResponse>("dreaming/settings"),
        hiveGet<DreamCycleRow[]>("dreaming/cycles?limit=24"),
      ]);
      setSettings(s);
      setFrequencyHours(Math.max(1, Math.min(168, Number(s.frequency_hours || 24))));
      setCycles(rows);
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Dreaming data unavailable.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function persist(nextEnabled: boolean): Promise<void> {
    setSaving(true);
    setError(null);
    try {
      const next = await hivePutJson<DreamingSettingsResponse>("dreaming/settings", {
        enabled: nextEnabled,
        frequency_hours: Math.max(1, Math.min(168, frequencyHours)),
      });
      setSettings(next);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Could not update dreaming settings.";
      setError(detail);
    } finally {
      setSaving(false);
    }
  }

  async function runNow(): Promise<void> {
    setRunning(true);
    setError(null);
    try {
      const out = await hivePostJson<RunNowResponse>("dreaming/run-now", {});
      setLastRunTaskId(out.celery_task_id);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Manual dreaming trigger failed.";
      setError(detail);
    } finally {
      setRunning(false);
    }
  }

  async function clearAllDreamSessions(): Promise<void> {
    if (!window.confirm("Clear all dream session reports for this tenant? This cannot be undone.")) {
      return;
    }
    setClearBusy(true);
    setError(null);
    try {
      const result = await hiveDelete<{ cleared: number }>("dreaming/cycles");
      toast.success(`Cleared ${result.cleared ?? 0} dream session${result.cleared === 1 ? "" : "s"}.`);
      await load();
    } catch (exc) {
      const detail = exc instanceof HiveApiError ? exc.message : "Could not clear dream sessions.";
      setError(detail);
      toast.error(detail);
    } finally {
      setClearBusy(false);
    }
  }

  const enabled = settings?.enabled ?? false;

  return (
    <div className="flex flex-col gap-8">
      <div className="v4-learning-lane">
        <Moon className="h-4 w-4 shrink-0 text-(--qs-purple-bright)" aria-hidden />
        <div>
          <p className="v4-label-kicker">Nightly memory lane</p>
          <p className="text-xs text-(--qs-text-3)">
            Celery beat consolidates supervisor history into HiveMind · tenant-scoped dream reports.
          </p>
        </div>
        {enabled ? <V4Badge tone="ok">Scheduled</V4Badge> : <V4Badge tone="warn">Paused</V4Badge>}
      </div>

      <V4Card>
        <V4CardHeader
          title="Dreaming · nightly memory cycles"
          description="Tenant-scoped consolidation of supervisor history into HiveMind knowledge and Dream Reports."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                disabled={running || loading}
                onClick={() => void runNow()}
              >
                {running ? <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Play className="h-3.5 w-3.5" aria-hidden />}
                {running ? "Queueing…" : "Run now"}
              </button>
              <button
                type="button"
                className={cn("qs-btn qs-btn--sm", enabled ? "qs-btn--ghost" : "qs-btn--primary")}
                disabled={saving || loading}
                onClick={() => void persist(!enabled)}
              >
                {saving ? "Saving…" : enabled ? "Disable dreaming" : "Enable dreaming"}
              </button>
            </div>
          }
        />

        {loading ? (
          <p className="mb-4 flex items-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden />
            Loading dreaming controls…
          </p>
        ) : null}
        {error ? <p className="mb-4 text-sm text-(--qs-red)">{error}</p> : null}

        <section className="v4-learning-panel">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-(--qs-text)">Memory + Dreaming</h3>
              <p className="mt-1 text-xs text-(--qs-text-3)">
                Automated learning — supervisor sessions → patterns, failures, Dream Report in HiveMind.
              </p>
            </div>
            <InfoHint
              title="What is Memory + Dreaming?"
              description="Automated learning. The system reads past supervisor sessions, finds useful patterns and mistakes, and saves a summary to HiveMind as a Dream Report."
              options={[
                "Learns without manual intervention",
                "Everything is tenant-scoped",
                "New insights appear in Knowledge",
              ]}
            />
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <label className="block">
              <span className="v4-field-label inline-flex items-center gap-2">
                Frequency (hours)
                <InfoHint
                  title="Dreaming frequency"
                  description="How often automatic learning runs. Lower values mean more frequent runs and higher compute use."
                  options={[
                    "24 = once daily (recommended)",
                    "1–8 = more frequent during active operations",
                    "168 = once weekly for low activity",
                  ]}
                />
              </span>
              <input
                type="number"
                min={1}
                max={168}
                value={frequencyHours}
                disabled={saving || loading}
                onChange={(event) => setFrequencyHours(Number(event.target.value || 24))}
                className="qs-input mt-1.5 min-h-11 w-full rounded-(--qs-radius-sm) font-mono"
              />
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm"
                disabled={running || loading}
                onClick={() => void runNow()}
              >
                {running ? "Queueing…" : "Run dreaming now"}
              </button>
              <InfoHint
                title="Run Dreaming now"
                description="Manual one-shot run. Use after major changes or a series of incidents to get a fresh Dream Report immediately."
                options={[
                  "Queues a single Celery job",
                  "Does not wait for the scheduled time",
                  "Results appear under Latest Dream Reports",
                ]}
              />
            </div>
          </div>

          {lastRunTaskId ? (
            <p className="mt-3 font-mono text-[11px] text-(--qs-cyan)">Manual run queued: {lastRunTaskId}</p>
          ) : null}
        </section>

        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2">
            <InfoHint
              title="Latest Dream Reports"
              description="Overview of recent Dreaming runs. Each card shows how much data was processed and how many duplicates were merged."
              options={[
                "status: run state (completed/failed)",
                "consolidated: count of new consolidated insights",
                "dedup: count of removed duplicate signals",
              ]}
            />
          </div>

          {loading ? (
            <DreamReportsGridSkeleton />
          ) : (
            <DreamReportsGrid
              cycles={cycles}
              clearBusy={clearBusy}
              onClear={() => void clearAllDreamSessions()}
            />
          )}
        </div>
      </V4Card>
    </div>
  );
}
