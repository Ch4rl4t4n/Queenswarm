"use client";

import { RefreshCw, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { TasksKanbanBoard } from "@/components/hive/tasks-kanban-board";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { TaskRow } from "@/lib/hive-types";
import {
  filterMissionKanbanTasks,
  uniqueAssignees,
} from "@/lib/mission-kanban";
import { MISSION_KANBAN_BUNDLES } from "@/lib/mission-kanban-bundles";
import { cn } from "@/lib/utils";

interface MissionKanbanDispatchResponse {
  task_id: string;
  child_count: number;
  execution: string;
}

interface MissionKanbanTriageResponse {
  task_id: string;
  title: string;
}

interface MissionKanbanPanelProps {
  onOpenTask?: (taskId: string) => void;
}

export function MissionKanbanPanel({ onOpenTask }: MissionKanbanPanelProps): JSX.Element {
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [assignee, setAssignee] = useState("all");
  const [showArchived, setShowArchived] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [triageMode, setTriageMode] = useState(true);

  const reload = useCallback(async () => {
    try {
      const rows = await hiveGet<TaskRow[]>("tasks?limit=200");
      setTasks(rows);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : "Failed to load kanban tasks";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  useEffect(() => {
    void reload();
  }, [reload]);

  const assignees = useMemo(() => uniqueAssignees(tasks), [tasks]);

  const filtered = useMemo(
    () =>
      filterMissionKanbanTasks(tasks, {
        query,
        assignee,
        showArchived,
      }),
    [tasks, query, assignee, showArchived],
  );

  const triageCount = useMemo(
    () => tasks.filter((t) => t.status.toLowerCase() === "triage").length,
    [tasks],
  );

  async function handleLaunchBundle(bundleId: string): Promise<void> {
    const bundle = MISSION_KANBAN_BUNDLES.find((b) => b.id === bundleId);
    if (!bundle) return;
    setBusy(true);
    try {
      const triage = await hivePostJson<MissionKanbanTriageResponse>("operator/mission-kanban/triage", {
        task_text: bundle.taskText,
        title: bundle.label,
        priority: 7,
      });
      if (bundle.autoDispatch) {
        const res = await hivePostJson<MissionKanbanDispatchResponse>(
          `operator/mission-kanban/dispatch/${encodeURIComponent(triage.task_id)}`,
          { start_execution: true, defer_to_worker: true },
        );
        toast.success(`${bundle.label} dispatched · ${res.child_count} child slices`);
      } else {
        toast.success(`${bundle.label} added to Triage — review then Dispatch.`);
      }
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Bundle launch failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAddTask(): Promise<void> {
    const text = newTitle.trim();
    if (text.length < 8) {
      toast.error("Enter at least 8 characters for the task prompt.");
      return;
    }
    setBusy(true);
    try {
      if (triageMode) {
        await hivePostJson<MissionKanbanTriageResponse>("operator/mission-kanban/triage", {
          task_text: text,
          title: text.split("\n")[0]?.slice(0, 500),
        });
        toast.success("Added to Triage — click Dispatch now to decompose.");
      } else {
        await hivePostJson<TaskRow>("tasks", {
          title: text.split("\n")[0]?.slice(0, 500) ?? "Hive task",
          task_type: "agent_run",
          priority: 5,
          payload: { mission_kanban: true },
        });
        toast.success("Task added to Todo.");
      }
      setNewTitle("");
      await reload();
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Could not create task");
    } finally {
      setBusy(false);
    }
  }

  async function handleDispatchAll(): Promise<void> {
    const triageTasks = tasks.filter((t) => t.status.toLowerCase() === "triage");
    if (!triageTasks.length) {
      toast.message("No triage tasks — add a big prompt with Triage checked.");
      return;
    }
    setBusy(true);
    let dispatched = 0;
    try {
      for (const t of triageTasks) {
        const res = await hivePostJson<MissionKanbanDispatchResponse>(
          `operator/mission-kanban/dispatch/${encodeURIComponent(t.id)}`,
          { start_execution: true, defer_to_worker: true },
        );
        dispatched += 1;
        toast.success(`Dispatched "${t.title}" · ${res.child_count} child slices`);
      }
      await reload();
      if (dispatched === 0) {
        toast.message("Nothing to dispatch.");
      }
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Dispatch failed");
    } finally {
      setBusy(false);
    }
  }

  async function handlePatchStatus(taskId: string, status: string): Promise<void> {
    try {
      await hivePatchJson(`tasks/${encodeURIComponent(taskId)}`, { status });
      await reload();
      toast.success(`Task moved to ${status}`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Status update failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-[color:var(--qs-border)] bg-hive-card/60 p-4">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-(--qs-text-2)">
          Mission Kanban — drop a big prompt into Triage, dispatch to decompose into child tasks, and
          watch bees move work across columns.
        </p>
        <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search tasks…"
              className="min-w-[160px] flex-1 rounded-xl border border-[color:var(--qs-border)] bg-black/45 px-3 py-2 text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
            />
            <select
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              className="rounded-xl border border-[color:var(--qs-border)] bg-black/45 px-3 py-2 text-sm text-[#fafafa] focus:border-pollen/35 focus:outline-none"
            >
              <option value="all">All assignees</option>
              {assignees.map((name) => (
                <option key={name} value={name.toLowerCase()}>
                  {name}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-xs text-zinc-400">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="rounded border-zinc-600"
              />
              Show done
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void reload()}
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", busy && "animate-spin")} aria-hidden />
              Refresh
            </button>
            <button
              type="button"
              disabled={busy || triageCount === 0}
              onClick={() => void handleDispatchAll()}
              className="qs-btn qs-btn--cyan qs-btn--sm gap-1.5"
            >
              <Send className="h-3.5 w-3.5" aria-hidden />
              Dispatch now{triageCount > 0 ? ` (${triageCount})` : ""}
            </button>
            <span className="text-xs text-zinc-500">
              {filtered.length}/{tasks.length} tasks
            </span>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void handleAddTask();
              }
            }}
            placeholder="+ New task title… (⌘+Enter to create)"
            className="min-w-0 flex-1 rounded-xl border border-[color:var(--qs-border)] bg-black/45 px-4 py-2.5 text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
          <label className="flex shrink-0 items-center gap-2 text-xs text-purple-300">
            <input
              type="checkbox"
              checked={triageMode}
              onChange={(e) => setTriageMode(e.target.checked)}
              className="rounded border-purple-500/50"
            />
            Triage
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={() => void handleAddTask()}
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
          >
            + Add
          </button>
        </div>

        <div className="mt-3">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Skill bundles</p>
          <div className="flex flex-wrap gap-2">
            {MISSION_KANBAN_BUNDLES.map((bundle) => (
              <button
                key={bundle.id}
                type="button"
                disabled={busy}
                title={bundle.hint}
                onClick={() => void handleLaunchBundle(bundle.id)}
                className="rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs text-purple-200 transition hover:border-purple-400/50 hover:bg-purple-500/20"
              >
                {bundle.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <p className="animate-pulse text-sm text-pollen">Loading mission kanban…</p>
      ) : (
        <TasksKanbanBoard
          tasks={filtered}
          onOpenTask={onOpenTask}
          onPatchStatus={(taskId, status) => void handlePatchStatus(taskId, status)}
        />
      )}
    </div>
  );
}
