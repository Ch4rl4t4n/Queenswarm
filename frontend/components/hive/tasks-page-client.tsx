"use client";

import dynamic from "next/dynamic";
import { InfoHint } from "@/components/hive/info-hint";
import { TasksListPanel } from "@/components/hive/tasks-list-panel";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import type { TaskRow } from "@/lib/hive-types";
import { useState } from "react";
import useSWR from "swr";

interface TasksPageClientProps {
  initialTasks: TaskRow[];
}

const SWR_KEY = "phase-j/tasks?limit=100";
const TaskResultDrawer = dynamic(
  () => import("@/components/hive/task-result-drawer").then((mod) => mod.TaskResultDrawer),
  { ssr: false },
);

export function TasksPageClient({ initialTasks }: TasksPageClientProps): JSX.Element {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const { data = initialTasks, error, isValidating, mutate } = useSWR<TaskRow[]>(
    SWR_KEY,
    () => hiveGet<TaskRow[]>("tasks?limit=100"),
    {
      fallbackData: initialTasks,
      refreshInterval: COCKPIT_POLL_BOARD_MS,
      revalidateOnFocus: true,
      dedupingInterval: 4_000,
      focusThrottleInterval: COCKPIT_POLL_BOARD_MS,
    },
  );

  return (
    <>
      {error ? (
        <div
          className="mb-4 flex flex-col gap-3 rounded-2xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger sm:flex-row sm:items-center sm:justify-between"
          role="alert"
        >
          <span className="font-(family-name:--font-poppins)">
            Task list sync failed — showing last known snapshot. {error instanceof Error ? error.message : "Unknown error"}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void mutate()}
              className="inline-flex min-h-[44px] shrink-0 items-center justify-center rounded-xl border border-danger/50 px-4 py-2 text-xs font-semibold text-danger hover:bg-danger/15 touch-manipulation"
            >
              Retry fetch
            </button>
            <InfoHint
              title="Retry fetch"
              description="Triggers immediate task list synchronization from backend API."
              options={["Manual refresh", "Recover stale snapshot", "Validate API connectivity"]}
            />
          </div>
        </div>
      ) : null}
      {isValidating && !error ? (
        <p className="mb-3 font-(family-name:--font-poppins) text-xs text-cyan/90" aria-live="polite">
          Refreshing tasks…
        </p>
      ) : null}
      <TasksListPanel onOpenTask={(id) => setSelectedTaskId(id)} tasks={data} />
      <TaskResultDrawer onClose={() => setSelectedTaskId(null)} taskId={selectedTaskId} />
    </>
  );
}
