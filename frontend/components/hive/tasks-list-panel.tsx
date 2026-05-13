"use client";

import type { JSX } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";

import type { TaskRow } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type StatusTab = "all" | "running" | "pending" | "completed";

function statusBadgeClass(statusRaw: string): string {
  const s = statusRaw.toUpperCase();
  if (s.includes("RUN")) return "border-data/45 bg-data/[0.12] text-data";
  if (s.includes("PEND") || s.includes("WAIT") || s.includes("QUEUE")) return "border-pollen/45 bg-pollen/[0.1] text-pollen";
  if (s.includes("COMP")) return "border-success/45 bg-success/[0.12] text-success";
  if (s.includes("FAIL") || s.includes("CANCEL")) return "border-danger/45 bg-danger/[0.12] text-danger";
  return "border-white/15 bg-black/35 text-zinc-400";
}

function matchesTab(statusRaw: string, tab: StatusTab): boolean {
  const s = statusRaw.toUpperCase();
  if (tab === "all") return true;
  if (tab === "running") return s.includes("RUN");
  if (tab === "pending") return s.includes("PEND") || s.includes("QUEUE") || (!s.includes("RUN") && !s.includes("COMP") && !s.includes("FAIL"));
  if (tab === "completed") return s.includes("COMP");
  return true;
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "—";
  const mins = Math.floor(ms / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function taskSteps(task: TaskRow): { done: number; total: number } {
  const p = task.payload;
  if (p && typeof p === "object") {
    const raw = p as Record<string, unknown>;
    const done = Number(raw.completed_steps ?? raw.step_completed ?? raw.current_step);
    const total = Number(raw.total_steps ?? raw.steps_total ?? raw.max_steps);
    if (!Number.isNaN(done) && !Number.isNaN(total) && total > 0) {
      return { done: Math.min(Math.max(0, done), total), total };
    }
  }
  const s = task.status.toUpperCase();
  if (s.includes("COMP")) return { done: 1, total: 1 };
  if (s.includes("FAIL")) return { done: 1, total: 1 };
  if (s.includes("RUN")) return { done: 2, total: 5 };
  return { done: 0, total: 5 };
}

function swarmBadge(task: TaskRow): string {
  const tt = (task.task_type ?? "").toLowerCase();
  if (tt.includes("scout")) return "scout";
  if (tt.includes("eval")) return "eval";
  if (tt.includes("sim")) return "sim";
  if (tt.includes("action")) return "action";
  return "hive";
}

function swarmBadgeClass(lane: string): string {
  if (lane === "scout") return "border-data/35 text-data";
  if (lane === "eval") return "border-pollen/35 text-pollen";
  if (lane === "sim") return "border-alert/35 text-alert";
  if (lane === "action") return "border-success/35 text-success";
  return "border-zinc-500/35 text-zinc-400";
}

interface TasksListPanelProps {
  tasks: TaskRow[];
  onOpenTask: (taskId: string) => void;
}

/** Filterable backlog table with swarm pills and heuristic progress bars. */
export function TasksListPanel({ tasks, onOpenTask }: TasksListPanelProps): JSX.Element {
  const [tab, setTab] = useState<StatusTab>("all");

  const filtered = useMemo(() => tasks.filter((t) => matchesTab(t.status, tab)), [tasks, tab]);

  function tabBtn(active: boolean): string {
    return cn(
      "rounded-full border px-3 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold transition",
      active ? "border-pollen/50 bg-pollen/10 text-pollen" : "border-transparent bg-black/45 text-zinc-500 hover:border-cyan/20 hover:text-zinc-300",
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", "All"],
              ["running", "Running"],
              ["pending", "Pending"],
              ["completed", "Completed"],
            ] as const
          ).map(([key, label]) => (
            <button key={key} type="button" className={tabBtn(tab === key)} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </div>
        <Link
          href="/tasks/new"
          className="inline-flex items-center justify-center gap-2 rounded-2xl border-[2px] border-pollen bg-pollen px-5 py-2.5 font-[family-name:var(--font-poppins)] text-sm font-bold text-black shadow-[0_0_24px_rgb(255_184_0/0.35)] hover:bg-[#ffc933]"
        >
          <Plus className="h-4 w-4" aria-hidden />+ New task
        </Link>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-cyan/[0.08] bg-[#07070f]/90">
        <table className="w-full min-w-[320px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-cyan/[0.08] font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              <th className="px-4 py-3">Task</th>
              <th className="hidden px-4 py-3 sm:table-cell">Swarm</th>
              <th className="px-4 py-3">Status</th>
              <th className="hidden px-4 py-3 lg:table-cell">Progress</th>
              <th className="hidden px-4 py-3 md:table-cell">Updated</th>
            </tr>
          </thead>
          <tbody className="font-[family-name:var(--font-inter)]">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-zinc-500">
                  No tasks in this lane.
                </td>
              </tr>
            ) : (
              filtered.map((t) => {
                const lane = swarmBadge(t);
                const { done, total } = taskSteps(t);
                const pct = total > 0 ? Math.round((done / total) * 100) : 0;
                return (
                  <tr key={t.id} className="border-b border-cyan/[0.05] hover:bg-white/[0.03]">
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => onOpenTask(t.id)}
                        className="block w-full text-left font-semibold text-[#fafafa] hover:text-pollen"
                      >
                        {t.title}
                      </button>
                      <span className="mt-1 block font-[family-name:var(--font-jetbrains-mono)] text-[10px] uppercase text-zinc-600">{t.task_type}</span>
                    </td>
                    <td className="hidden px-4 py-3 sm:table-cell">
                      <span
                        className={cn(
                          "inline-flex rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase",
                          swarmBadgeClass(lane),
                        )}
                      >
                        {lane}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("inline-flex rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase", statusBadgeClass(t.status))}>
                        {t.status.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td className="hidden px-4 py-3 lg:table-cell">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-black/60">
                          <div className="h-full rounded-full bg-gradient-to-r from-data to-pollen shadow-[0_0_12px_rgb(0_255_255/0.25)]" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-zinc-500">
                          {done}/{total}
                        </span>
                      </div>
                    </td>
                    <td className="hidden whitespace-nowrap px-4 py-3 font-[family-name:var(--font-jetbrains-mono)] text-xs text-zinc-500 md:table-cell">{timeAgo(t.updated_at)}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
