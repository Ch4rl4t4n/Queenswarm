"use client";

import { Pencil, Trash2 } from "lucide-react";
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
import { formatDurationSeconds } from "@/lib/format-relative-time";


function formatKanbanAge(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const parsed = Date.parse(dateStr);
  if (Number.isNaN(parsed)) return "";
  const sec = Math.floor((Date.now() - parsed) / 1000);
  if (sec < 60) return "just now";
  return formatDurationSeconds(sec);
}

interface TasksKanbanBoardProps {
  tasks: TaskRow[];
  onOpenTask?: (taskId: string, opts?: { edit?: boolean }) => void;
  onPatchStatus?: (taskId: string, status: string) => void;
  onDeleteTask?: (taskId: string) => void;
  selectedDoneIds?: Set<string>;
  onToggleDoneSelect?: (taskId: string) => void;
  onClearAllDone?: (taskIds: string[]) => void;
  onDeleteSelectedDone?: (taskIds: string[]) => void;
}

export function TasksKanbanBoard({
  tasks,
  onOpenTask,
  onPatchStatus,
  onDeleteTask,
  selectedDoneIds,
  onToggleDoneSelect,
  onClearAllDone,
  onDeleteSelectedDone,
}: TasksKanbanBoardProps): JSX.Element {
  const grouped = useMemo(() => groupMissionKanbanTasks(tasks), [tasks]);

  return (
    <div className="pb-2 max-lg:overflow-x-auto lg:overflow-visible">
      <div className="flex max-lg:min-w-[960px] gap-3 max-lg:pb-1 lg:grid lg:min-w-0 lg:w-full lg:grid-cols-6">
        {MISSION_KANBAN_COLUMN_ORDER.map((colKey) => {
          const col = MISSION_KANBAN_COLUMN_CONFIG[colKey];
          const columnTasks = grouped[colKey];
          const selectedInColumn =
            colKey === "done" && selectedDoneIds
              ? columnTasks.filter((t) => selectedDoneIds.has(String(t.id))).length
              : 0;
          return (
            <section
              key={colKey}
              className={cn(
                "flex w-[220px] shrink-0 flex-col rounded-2xl border bg-hive-card/90 p-3 shadow-inner",
                "lg:min-w-0 lg:w-auto",
                col.tint,
              )}
            >
              <header className="mb-3 flex shrink-0 flex-col gap-2 border-b border-white/[0.06] pb-2">
                <div className="flex items-center gap-2">
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
                </div>
                {colKey === "done" && columnTasks.length > 0 && onClearAllDone ? (
                  <div className="flex flex-wrap items-center gap-1.5">
                    {selectedInColumn > 0 && onDeleteSelectedDone ? (
                      <button
                        type="button"
                        title="Remove selected done tasks"
                        className="rounded-md border border-danger/35 bg-danger/10 px-2 py-0.5 font-[family-name:var(--font-poppins)] text-[10px] text-danger transition hover:border-danger/55 hover:bg-danger/15"
                        onClick={() =>
                          onDeleteSelectedDone(
                            columnTasks
                              .filter((t) => selectedDoneIds?.has(String(t.id)))
                              .map((t) => String(t.id)),
                          )
                        }
                      >
                        Delete {selectedInColumn}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      title="Remove all done tasks from kanban"
                      className="rounded-md border border-white/10 px-2 py-0.5 font-[family-name:var(--font-poppins)] text-[10px] text-zinc-400 transition hover:border-danger/35 hover:text-danger"
                      onClick={() => onClearAllDone(columnTasks.map((t) => String(t.id)))}
                    >
                      Clear all
                    </button>
                  </div>
                ) : null}
              </header>
              <ul className="flex max-h-[65vh] flex-col gap-2 overflow-y-auto pr-1 hive-scrollbar">
                {columnTasks.map((t) => (
                  <KanbanCard
                    key={t.id}
                    task={t}
                    column={colKey}
                    onOpenTask={onOpenTask}
                    onPatchStatus={onPatchStatus}
                    onDeleteTask={onDeleteTask}
                    selected={colKey === "done" && selectedDoneIds?.has(String(t.id))}
                    onToggleSelect={
                      colKey === "done" && onToggleDoneSelect
                        ? () => onToggleDoneSelect(String(t.id))
                        : undefined
                    }
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
  onDeleteTask,
  selected = false,
  onToggleSelect,
}: {
  task: TaskRow;
  column: MissionKanbanColumn;
  onOpenTask?: (taskId: string, opts?: { edit?: boolean }) => void;
  onPatchStatus?: (taskId: string, status: string) => void;
  onDeleteTask?: (taskId: string) => void;
  selected?: boolean;
  onToggleSelect?: () => void;
}): JSX.Element {
  const assignee = task.agent_name ?? "—";
  const isRunning = task.status.toLowerCase() === "running";
  const isDone = column === "done";

  return (
    <li>
      <div
        className={cn(
          "rounded-xl border border-[color:var(--qs-border-2)]/[0.08] bg-black/35 p-3",
          isDone && selected && "border-success/35 bg-success/5",
        )}
      >
        <div className="flex items-start gap-2">
          {onToggleSelect ? (
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggleSelect}
              aria-label={`Select ${task.title}`}
              className="mt-1 shrink-0 rounded border-zinc-600 accent-success"
            />
          ) : null}
          <button
            type="button"
            onClick={() => onOpenTask?.(String(task.id))}
            disabled={!onOpenTask}
            className={cn(
              "min-w-0 flex-1 text-left transition",
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
                {formatKanbanAge(task.updated_at ?? task.created_at)}
              </span>
            </div>
          </button>
          <div className="flex shrink-0 flex-col gap-1">
            {onOpenTask ? (
              <button
                type="button"
                title="Edit task"
                className="rounded-md border border-white/10 p-1 text-zinc-400 transition hover:border-pollen/30 hover:text-pollen"
                onClick={() => onOpenTask(String(task.id), { edit: true })}
              >
                <Pencil className="h-3 w-3" aria-hidden />
              </button>
            ) : null}
            {onDeleteTask && !isRunning ? (
              <button
                type="button"
                title="Remove task"
                className={cn(
                  "rounded-md border border-white/10 p-1 text-zinc-400 transition hover:border-danger/40 hover:text-danger",
                  isDone && "border-danger/25 text-danger/80 hover:bg-danger/10",
                )}
                onClick={() => onDeleteTask(String(task.id))}
              >
                <Trash2 className="h-3 w-3" aria-hidden />
              </button>
            ) : null}
          </div>
        </div>
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
