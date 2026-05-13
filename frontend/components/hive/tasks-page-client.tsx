"use client";

import { TasksListPanel } from "@/components/hive/tasks-list-panel";
import { TaskResultDrawer } from "@/components/hive/task-result-drawer";
import { hiveGet } from "@/lib/api";
import type { TaskRow } from "@/lib/hive-types";
import { useState } from "react";
import useSWR from "swr";

interface TasksPageClientProps {
  initialTasks: TaskRow[];
}

const SWR_KEY = "phase-j/tasks?limit=100";

export function TasksPageClient({ initialTasks }: TasksPageClientProps): JSX.Element {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const { data = initialTasks } = useSWR<TaskRow[]>(
    SWR_KEY,
    () => hiveGet<TaskRow[]>("tasks?limit=100"),
    { fallbackData: initialTasks, refreshInterval: 8000, revalidateOnFocus: true },
  );

  return (
    <>
      <TasksListPanel onOpenTask={(id) => setSelectedTaskId(id)} tasks={data} />
      <TaskResultDrawer onClose={() => setSelectedTaskId(null)} taskId={selectedTaskId} />
    </>
  );
}
