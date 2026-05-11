import { hiveServerRawJson } from "@/lib/hive-server";
import type { TaskRow } from "@/lib/hive-types";

export const dynamic = "force-dynamic";

export default async function TasksPage() {
  const tasks = await hiveServerRawJson<TaskRow[]>("/tasks?limit=100");

  if (!tasks) {
    return <p className="text-danger font-[family-name:var(--font-jetbrains-mono)] text-sm">Task ledger unavailable.</p>;
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-[family-name:var(--font-space-grotesk)] text-3xl font-semibold text-pollen">
          scout backlog · rapid loop queue
        </h1>
        <p className="mt-2 font-[family-name:var(--font-jetbrains-mono)] text-sm text-cyan">
          Celery stubs queue hourly YouTube crypto pulses alongside operator-submitted intents.
        </p>
      </header>
      <div className="space-y-3">
        {tasks.map((task) => (
          <article
            key={task.id}
            className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-cyan/20 bg-black/35 p-4"
          >
            <div className="max-w-xl">
              <p className="font-[family-name:var(--font-space-grotesk)] text-lg font-semibold text-[#FFB800]">
                {task.title}
              </p>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs uppercase tracking-[0.2em] text-cyan">
                {task.task_type} · prio {task.priority}
              </p>
            </div>
            <div className="text-right font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted-foreground">
              <p className="text-data">{task.status}</p>
              {task.created_at ? <p>{new Date(task.created_at).toISOString()}</p> : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
