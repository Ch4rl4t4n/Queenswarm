"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Download, FileText, MicIcon, ShieldCheck } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";

import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { formatTimeAgoSeconds } from "@/lib/format-relative-time";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { TaskQueueItem, TaskQueueResponse } from "@/lib/hive-types";

export interface MissionResultsPanelProps {
  /** Open a task in the result drawer (download + replay live there). */
  onOpenTask?: (taskId: string) => void;
}

/**
 * Vysledky dna — completed tasks + handoff to Jarvis (Analytics) / Ballroom.
 *
 * The end of the daily workflow: a verified result you can download or analyze.
 */
function MissionResultsPanelInner({ onOpenTask }: MissionResultsPanelProps): JSX.Element {
  const [queue, setQueue] = useState<TaskQueueResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<TaskQueueResponse>("dashboard/task-queue?limit=100");
      setQueue(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Task queue unreachable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  const completed = useMemo(
    () => (queue?.tasks ?? []).filter((task: TaskQueueItem) => task.status.toLowerCase() === "completed").slice(0, 12),
    [queue?.tasks],
  );

  if (loading && !queue) {
    return <HivePanelSectionSkeleton label="Loading results" minHeightClass="min-h-[12rem]" />;
  }

  return (
    <V4Card data-testid="mission-results-panel">
      <V4CardHeader
        kicker="Výsledok"
        title="Výsledky dnes"
        description="Dokončené úlohy a výstupy — stiahni alebo analyzuj Jarvisom / v Ballroome."
        hint={sectionHintNode("missionResults")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {typeof queue?.completed_today_count === "number" ? (
              <V4Badge tone="ok">{queue.completed_today_count} dnes</V4Badge>
            ) : null}
            <HiveRefreshButton busy={loading} onClick={() => void reload()} />
          </div>
        }
      />

      <div className="flex flex-wrap gap-2 px-4 pb-3">
        <Link href="/apps-tools/analytics" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1.5">
          <BarChart3 className="size-3.5" aria-hidden />
          Analyzuj Jarvisom
        </Link>
        <Link href="/ballroom" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1.5">
          <MicIcon className="size-3.5" aria-hidden />
          Pošli do Ballroom
        </Link>
        <Link href="/knowledge#outputs" className="qs-btn qs-btn--ghost qs-btn--sm inline-flex gap-1.5">
          <FileText className="size-3.5" aria-hidden />
          Všetky výstupy
        </Link>
      </div>

      {err ? (
        <p className="px-4 pb-4 text-xs text-[#FF3366]" role="alert">
          {err}
        </p>
      ) : completed.length === 0 ? (
        <p className="flex items-center gap-2 px-4 pb-4 text-sm text-(--qs-muted)">
          <ShieldCheck className="size-4 text-[#00FF88]" aria-hidden />
          Zatiaľ žiadny dokončený výstup dnes — dokonči úlohu na Boarde.
        </p>
      ) : (
        <ul className="space-y-2 px-4 pb-4">
          {completed.map((task) => (
            <li
              key={task.id}
              className="flex flex-wrap items-center gap-2 rounded-lg border border-(--qs-border)/50 bg-black/20 p-3"
            >
              <V4Badge tone="ok">done</V4Badge>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold text-(--qs-text)">{task.title}</div>
                <div className="mt-0.5 text-xs text-(--qs-text-3)">
                  {task.short_id} · {formatTimeAgoSeconds(task.seconds_ago)}
                </div>
              </div>
              {onOpenTask ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-1.5"
                  onClick={() => onOpenTask(task.id)}
                >
                  <Download className="size-3.5" aria-hidden />
                  Stiahni
                </button>
              ) : (
                <Link href={`/tasks?task=${encodeURIComponent(task.id)}`} className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-1.5">
                  <Download className="size-3.5" aria-hidden />
                  Stiahni
                  <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </V4Card>
  );
}

export const MissionResultsPanel = memo(MissionResultsPanelInner);
MissionResultsPanel.displayName = "MissionResultsPanel";
