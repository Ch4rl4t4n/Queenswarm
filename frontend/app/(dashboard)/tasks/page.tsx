import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SectionNavGrid } from "@/components/hive/section-nav-grid";
import { TasksPageClient } from "@/components/hive/tasks-page-client";
import { TasksNewTaskActions, TasksQueueHeaderStats } from "@/components/hive/tasks-queue-section";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";
import { hiveServerRawJson } from "@/lib/hive-server";
import type { TaskRow } from "@/lib/hive-types";
import { deriveTaskCounts } from "@/lib/tasks-queue-utils";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await hiveServerRawJson<TaskRow[]>("/tasks?limit=100");

  if (!tasks) {
    return <p className="font-(family-name:--font-poppins) text-sm text-danger">Task ledger unavailable.</p>;
  }

  const counts = deriveTaskCounts(tasks);

  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Tasks"
        info={{
          title: "Tasks + Routines",
          description: "Execution fronta pre jednorazové úlohy a periodické routines.",
          options: ["Nový task", "Workflow prehľad", "Routine orchestration"],
        }}
        subtitle={
          <>
            <TasksQueueHeaderStats counts={counts} />
          </>
        }
        actions={<TasksNewTaskActions />}
      />
      <SectionNavGrid
        items={[
          { href: "/tasks/new", title: "New task", description: "Compose and dispatch a mission into the hive queue." },
          { href: "/workflows", title: "Workflows", description: "Visual DAG execution, pause/resume, and run controls." },
          { href: "/jobs", title: "Jobs", description: "Inspect async execution jobs, retries, and completion state." },
          { href: "/agents", title: "Routines", description: "Manage supervisor routines and schedule-driven task execution." },
          ...(SIMULATIONS_ENABLED
            ? [{ href: "/simulations", title: "Simulations", description: "Verified simulation ledger and compliance snapshots." }]
            : []),
        ]}
      />
      <TasksPageClient initialTasks={tasks} />
    </div>
  );
}
