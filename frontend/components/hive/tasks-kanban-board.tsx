"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type ColumnKey = "queued" | "running" | "completed" | "failed";

const COLUMN_CONFIG: Record<
  ColumnKey,
  { label: string; tint: string; headerColor: string; dot: string }
> = {
  queued: {
    label: "Queued",
    tint: "border-pollen/35 text-pollen",
    headerColor: "#FFB800",
    dot: "bg-pollen",
  },
  running: {
    label: "Running",
    tint: "border-data/35 text-data",
    headerColor: "#00FFFF",
    dot: "animate-pulse bg-data",
  },
  completed: {
    label: "Completed",
    tint: "border-success/35 text-success",
    headerColor: "#00FF88",
    dot: "bg-success",
  },
  failed: {
    label: "Failed",
    tint: "border-danger/35 text-danger",
    headerColor: "#FF3366",
    dot: "bg-danger",
  },
};

const COLUMN_ORDER: ColumnKey[] = ["queued", "running", "completed", "failed"];

function columnFor(statusRaw: string): ColumnKey {
  const s = statusRaw.toUpperCase();
  if (s.includes("RUN")) return "running";
  if (s.includes("COMP")) return "completed";
  if (s.includes("FAIL") || s.includes("CANCEL")) return "failed";
  return "queued";
}

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function confidenceFrac(task: TaskRow): number | null {
  if (typeof task.confidence_score === "number") {
    return Math.max(0, Math.min(1, task.confidence_score));
  }
  const r = task.result;
  if (!r || typeof r !== "object") return null;
  const pct = Number((r as { confidence_pct?: unknown }).confidence_pct);
  return Number.isNaN(pct) ? null : Math.max(0, Math.min(1, pct / 100));
}

interface TasksKanbanBoardProps {
  tasks: TaskRow[];
  onOpenTask?: (taskId: string) => void;
}

export function TasksKanbanBoard({ tasks, onOpenTask }: TasksKanbanBoardProps): JSX.Element {
  const [swarmNeedle, setSwarmNeedle] = useState("");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const sn = swarmNeedle.trim().toLowerCase();
    const nq = q.trim().toLowerCase();
    return tasks.filter((t) => {
      const swarmOk = sn === "" || (t.swarm_id ?? "").toLowerCase().includes(sn);
      const needle = `${t.title} ${t.task_type} ${t.id} ${t.agent_name ?? ""}`;
      const textOk = nq === "" || needle.toLowerCase().includes(nq);
      return swarmOk && textOk;
    });
  }, [tasks, swarmNeedle, q]);

  const grouped = useMemo(() => {
    const init: Record<ColumnKey, TaskRow[]> = { queued: [], running: [], completed: [], failed: [] };
    for (const t of filtered) {
      init[columnFor(t.status)].push(t);
    }
    return init;
  }, [filtered]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500">
          <span className="rounded-full border border-cyan/[0.12] px-3 py-1">
            Hive Kanban · {filtered.length}/{tasks.length} visible
          </span>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title / type / bee…"
            className="min-w-0 flex-1 rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
          <input
            value={swarmNeedle}
            onChange={(e) => setSwarmNeedle(e.target.value)}
            placeholder="Filter swarm UUID fragment…"
            className="min-w-[200px] rounded-xl border border-cyan/[0.15] bg-black/45 px-4 py-2 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
          />
        </div>
        <NeonTasksNew />
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {COLUMN_ORDER.map((colKey) => {
          const col = COLUMN_CONFIG[colKey];
          const columnTasks = grouped[colKey];
          return (
            <section
              key={colKey}
              className={cn(
                "flex max-h-[70vh] flex-col rounded-2xl border bg-hive-card/90 p-3 shadow-inner hive-scrollbar",
                col.tint,
              )}
            >
              <header className="mb-3 flex shrink-0 items-center gap-2 border-b border-white/[0.06] pb-2">
                <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", col.dot)} />
                <span
                  className="font-[family-name:var(--font-poppins)] text-sm font-semibold"
                  style={{ color: col.headerColor }}
                >
                  {col.label}
                </span>
                <span className="ml-auto font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                  {columnTasks.length}
                </span>
              </header>
              <ul className="flex flex-1 flex-col gap-2 overflow-y-auto pr-1">
                {columnTasks.map((t) => {
                  const conf = confidenceFrac(t);
                  return (
                    <li key={t.id}>
                      <button
                        type="button"
                        onClick={() => onOpenTask?.(String(t.id))}
                        disabled={!onOpenTask}
                        className={cn(
                          "w-full rounded-xl border border-cyan/[0.08] bg-black/35 p-3 text-left transition hover:border-pollen/30",
                          onOpenTask ? "cursor-pointer" : "opacity-95",
                        )}
                      >
                        <p className="font-[family-name:var(--font-inter)] text-sm font-medium text-[#fafafa]">{t.title}</p>
                        <div className="mt-2 flex items-center justify-between gap-2">
                          <span className="truncate font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase text-zinc-500">
                            {t.agent_name ?? (t.agent_id ? `${String(t.agent_id).slice(0, 8)}…` : "—")}
                          </span>
                          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-600">
                            {timeAgo(t.created_at)}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.14em] text-zinc-500">
                          <span>{t.task_type}</span>
                          <span>p{t.priority}</span>
                        </div>
                        {conf !== null ? (
                          <div className="mt-2 flex items-center gap-1">
                            <div className="h-1 flex-1 overflow-hidden rounded-full bg-[#1a1a3e]">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-pollen to-success"
                                style={{ width: `${Math.round(conf * 100)}%` }}
                              />
                            </div>
                            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-600">
                              {Math.round(conf * 100)}%
                            </span>
                          </div>
                        ) : (
                          <ConfidenceHint result={t.result} />
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function ConfidenceHint({ result }: { result?: TaskRow["result"] }): JSX.Element | null {
  if (!result || typeof result !== "object") {
    return null;
  }
  const raw = "confidence_pct" in result ? (result as { confidence_pct?: unknown }).confidence_pct : undefined;
  const pct = typeof raw === "number" ? raw : null;
  if (pct === null) {
    return null;
  }
  return (
    <p className="mt-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-data">
      confidence {pct.toFixed(1)}%
    </p>
  );
}

function NeonTasksNew(): JSX.Element {
  return (
    <Link href="/tasks/new" className={cn("qs-btn qs-btn--primary qs-btn--sm")}>
      + New Task
    </Link>
  );
}
