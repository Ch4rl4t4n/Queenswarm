import { HivePageHeader } from "@/components/hive/hive-page-header";
import { TasksKanbanBoard } from "@/components/hive/tasks-kanban-board";
import { deriveTaskCounts, TasksNewTaskActions, TasksQueueHeaderStats } from "@/components/hive/tasks-queue-section";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await hiveServerRawJson<TaskRow[]>("/tasks?limit=100");

  if (!tasks) {
    return <p className="font-[family-name:var(--font-jetbrains-mono)] text-sm text-danger">Task ledger unavailable.</p>;
  }

  const counts = deriveTaskCounts(tasks);

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Task Queue"
        subtitle={
          <>
            <TasksQueueHeaderStats counts={counts} />
          </>
        }
        actions={<TasksNewTaskActions />}
      />
      <TasksKanbanBoard tasks={tasks} />
    </div>
  );
}
