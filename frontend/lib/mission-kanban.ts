/** Hermes-style mission kanban column mapping and helpers. */

import type { TaskRow } from "@/lib/hive-types";

export type MissionKanbanColumn =
  | "triage"
  | "todo"
  | "ready"
  | "running"
  | "blocked"
  | "done";

export const MISSION_KANBAN_COLUMN_ORDER: MissionKanbanColumn[] = [
  "triage",
  "todo",
  "ready",
  "running",
  "blocked",
  "done",
];

export const MISSION_KANBAN_COLUMN_CONFIG: Record<
  MissionKanbanColumn,
  { label: string; tint: string; headerColor: string; dot: string }
> = {
  triage: {
    label: "Triage",
    tint: "border-purple-400/35 text-purple-300",
    headerColor: "#A855F7",
    dot: "bg-purple-400",
  },
  todo: {
    label: "Todo",
    tint: "border-zinc-500/35 text-zinc-300",
    headerColor: "#A1A1AA",
    dot: "bg-zinc-400",
  },
  ready: {
    label: "Ready",
    tint: "border-data/35 text-data",
    headerColor: "#00FFFF",
    dot: "bg-data",
  },
  running: {
    label: "Running",
    tint: "border-pollen/35 text-pollen",
    headerColor: "#FFB800",
    dot: "animate-pulse bg-pollen",
  },
  blocked: {
    label: "Blocked",
    tint: "border-alert/35 text-alert",
    headerColor: "#FF00AA",
    dot: "bg-alert",
  },
  done: {
    label: "Done",
    tint: "border-success/35 text-success",
    headerColor: "#00FF88",
    dot: "bg-success",
  },
};

/** Map backend task status to mission kanban column. */
export function missionKanbanColumnFor(statusRaw: string): MissionKanbanColumn {
  const s = statusRaw.toLowerCase();
  if (s === "triage") return "triage";
  if (s === "ready") return "ready";
  if (s === "running") return "running";
  if (s === "blocked") return "blocked";
  if (s === "completed") return "done";
  if (s === "failed" || s === "cancelled") return "blocked";
  return "todo";
}

export function shortTaskId(id: string): string {
  const clean = id.replace(/-/g, "");
  return `t_${clean.slice(0, 8)}`;
}

export function uniqueAssignees(tasks: TaskRow[]): string[] {
  const names = new Set<string>();
  for (const t of tasks) {
    const label = t.agent_name?.trim();
    if (label) names.add(label);
  }
  return [...names].sort((a, b) => a.localeCompare(b));
}

export function filterMissionKanbanTasks(
  tasks: TaskRow[],
  opts: { query: string; assignee: string; showArchived: boolean },
): TaskRow[] {
  const q = opts.query.trim().toLowerCase();
  const assignee = opts.assignee.trim().toLowerCase();
  return tasks.filter((t) => {
    const col = missionKanbanColumnFor(t.status);
    if (!opts.showArchived && col === "done") {
      return false;
    }
    if (assignee !== "" && assignee !== "all") {
      const name = (t.agent_name ?? "").toLowerCase();
      if (name !== assignee) return false;
    }
    if (q === "") return true;
    const needle = `${t.title} ${t.task_type} ${t.id} ${t.agent_name ?? ""}`.toLowerCase();
    return needle.includes(q);
  });
}

export function groupMissionKanbanTasks(tasks: TaskRow[]): Record<MissionKanbanColumn, TaskRow[]> {
  const init: Record<MissionKanbanColumn, TaskRow[]> = {
    triage: [],
    todo: [],
    ready: [],
    running: [],
    blocked: [],
    done: [],
  };
  for (const t of tasks) {
    init[missionKanbanColumnFor(t.status)].push(t);
  }
  return init;
}
