import type { TaskRow } from "@/lib/hive-types";

function classifyStatus(status: string): "running" | "pending" | "completed" {
  const upper = status.toUpperCase();
  if (upper.includes("COMPLETE") || upper.includes("DONE") || upper.includes("SUCCESS")) {
    return "completed";
  }
  if (upper.includes("RUN") || upper.includes("ACTIVE") || upper.includes("PROCESS") || upper.includes("BUSY")) {
    return "running";
  }
  return "pending";
}

export interface TaskCounts {
  active: number;
  pending: number;
  completed: number;
  running: number;
}

export function deriveTaskCounts(tasks: TaskRow[]): TaskCounts {
  let running = 0;
  let pending = 0;
  let completed = 0;
  for (const task of tasks) {
    const bucket = classifyStatus(task.status);
    if (bucket === "running") running += 1;
    else if (bucket === "pending") pending += 1;
    else completed += 1;
  }
  return { active: running + pending, pending, completed, running };
}

