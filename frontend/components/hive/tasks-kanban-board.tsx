"use client";

import { useMemo } from "react";

import type { TaskRow } from "@/lib/hive-types";
import {
  groupMissionKanbanTasks,
  MISSION_KANBAN_COLUMN_CONFIG,
  MISSION_KANBAN_COLUMN_ORDER,
  missionKanbanColumnFor,
  shortTaskId,
  type MissionKanbanColumn,
} from "@/lib/mission-kanban";
import { cn } from "@/lib/utils";

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

interface TasksKanbanBoardProps {
  tasks: TaskRow[];
  onOpenTask?: (taskId: string) => void;
  onPatchStatus?: (taskId: string, status: string) => void;
}

export function TasksKanbanBoard({
  tasks,
  onOpenTask,
  onPatchStatus,
}: TasksKanbanBoardProps): JSX.Element {
  const grouped = useMemo(() => groupMissionKanbanTasks(tasks), [tasks]);

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-[960px] gap-3">
        {MISSION_KANBAN_COLUMN_ORDER.map((colKey) => {
          const col = MISSION_KANBAN_COLUMN_CONFIG[colKey];
          const columnTasks = grouped[colKey];
          return (
            <section
              key={colKey}
              className={cn(
                "flex w-[220px] shrink-0 flex-col rounded-2xl border bg-hive-card/90 p-3 shadow-inner",
                col.tint,
              )}
            >
              <header className="mb-3 flex shrink-0 items-center gap-2 border-b border-white/[0.06] pb-2">
                <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", col.dot)} />
                <span
                  className="font-[family-name:var(--font-poppins)] text-xs font-semibold uppercase tracking-wide"
                  style={{ color: col.headerColor }}
                >
                  {col.label}
                </span>
                <span className="ml-auto font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
                  {columnTasks.length}
                </span>
              </header>
              <ul className="flex max-h-[65vh] flex-col gap-2 overflow-y-auto pr-1 hive-scrollbar">
                {columnTasks.map((t) => (
                  <KanbanCard
                    key={t.id}
                    task={t}
                    column={colKey}
                    onOpenTask={onOpenTask}
                    onPatchStatus={onPatchStatus}
                  />
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function KanbanCard({
  task,
  column,
  onOpenTask,
  onPatchStatus,
}: {
  task: TaskRow;
  column: MissionKanbanColumn;
  onOpenTask?: (taskId: string) => void;
  onPatchStatus?: (taskId: string, status: string) => void;
}): JSX.Element {
  const assignee = task.agent_name ?? "—";

  return (
    <li>
      <div className="rounded-xl border border-[color:var(--qs-border-2)]/[0.08] bg-black/35 p-3">
        <button
          type="button"
          onClick={() => onOpenTask?.(String(task.id))}
          disabled={!onOpenTask}
          className={cn(
            "w-full text-left transition",
            onOpenTask ? "cursor-pointer hover:opacity-90" : "opacity-95",
          )}
        >
          <p className="font-[family-name:var(--font-poppins)] text-sm font-medium leading-snug text-[#fafafa]">
            {task.title}
          </p>
          <div className="mt-2 flex items-center justify-between gap-2">
            <span className="truncate font-[family-name:var(--font-poppins)] text-[10px] uppercase text-zinc-500">
              {assignee}
            </span>
            <span className="font-mono text-[10px] text-zinc-600">{shortTaskId(String(task.id))}</span>
            <span className="font-[family-name:var(--font-poppins)] text-[10px] text-zinc-600">
              {timeAgo(task.updated_at ?? task.created_at)}
            </span>
          </div>
        </button>
        {onPatchStatus && column !== "done" ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {column === "triage" ? (
              <MiniAction
                label="→ Todo"
                onClick={() => onPatchStatus(String(task.id), "pending")}
              />
            ) : null}
            {column === "todo" ? (
              <MiniAction
                label="→ Ready"
                onClick={() => onPatchStatus(String(task.id), "ready")}
              />
            ) : null}
            {column !== "blocked" && column !== "triage" ? (
              <MiniAction
                label="Block"
                onClick={() => onPatchStatus(String(task.id), "blocked")}
              />
            ) : null}
            {column === "blocked" ? (
              <MiniAction
                label="Unblock"
                onClick={() => onPatchStatus(String(task.id), "pending")}
              />
            ) : null}
            {column !== "triage" ? (
              <MiniAction
                label="Done"
                onClick={() => onPatchStatus(String(task.id), "completed")}
              />
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}

function MiniAction({ label, onClick }: { label: string; onClick: () => void }): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md border border-white/10 px-1.5 py-0.5 font-[family-name:var(--font-poppins)] text-[10px] text-zinc-400 transition hover:border-pollen/30 hover:text-pollen"
    >
      {label}
    </button>
  );
}

export { missionKanbanColumnFor };
