"use client";

import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { HiveApiError, hiveGet } from "@/lib/api";
import type { TaskQueueItem, TaskQueueResponse } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type StatusTab = "all" | "running" | "pending" | "completed";

function laneAccent(lane: string): string {
  const L = lane.toLowerCase();
  if (L === "scout") {
    return "bg-cyan";
  }
  if (L === "eval") {
    return "bg-pollen";
  }
  if (L === "sim") {
    return "bg-alert";
  }
  return "bg-success";
}

function swarmPillClass(lane: string): string {
  const L = lane.toLowerCase();
  if (L === "scout") {
    return "border-cyan/45 bg-cyan/[0.12] text-cyan";
  }
  if (L === "eval") {
    return "border-pollen/45 bg-pollen/[0.1] text-pollen";
  }
  if (L === "sim") {
    return "border-alert/45 bg-alert/[0.1] text-alert";
  }
  return "border-success/45 bg-success/[0.1] text-success";
}

function progressFillClass(lane: string, status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") {
    return "bg-pollen";
  }
  return laneAccent(lane);
}

function progressPctTextClass(lane: string, status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") {
    return "text-pollen";
  }
  const L = lane.toLowerCase();
  if (L === "scout") {
    return "text-cyan";
  }
  if (L === "eval") {
    return "text-pollen";
  }
  if (L === "sim") {
    return "text-alert";
  }
  return "text-success";
}

function statusDotAndLabel(status: string): { dot: string; label: string } {
  const s = status.toLowerCase();
  if (s === "running") {
    return { dot: "bg-success shadow-[0_0_6px_rgb(0_255_136/0.6)]", label: "running" };
  }
  if (s === "pending") {
    return { dot: "bg-pollen shadow-[0_0_6px_rgb(255_184_0/0.45)]", label: "pending" };
  }
  if (s === "completed") {
    return { dot: "bg-cyan shadow-[0_0_6px_rgb(0_255_255/0.45)]", label: "completed" };
  }
  if (s === "failed") {
    return { dot: "bg-danger", label: "failed" };
  }
  if (s === "cancelled") {
    return { dot: "bg-zinc-500", label: "cancelled" };
  }
  return { dot: "bg-zinc-500", label: s };
}

function formatQueueAgo(sec: number): string {
  if (sec < 60) {
    return `${sec}s`;
  }
  const m = Math.floor(sec / 60);
  if (m < 120) {
    return `${m}m`;
  }
  const h = Math.floor(m / 60);
  return `${h}h`;
}

function matchesTab(item: TaskQueueItem, tab: StatusTab): boolean {
  const s = item.status.toLowerCase();
  if (tab === "all") {
    return true;
  }
  if (tab === "running") {
    return s === "running";
  }
  if (tab === "pending") {
    return s === "pending";
  }
  if (tab === "completed") {
    return s === "completed";
  }
  return true;
}

export function TaskQueueSection() {
  const [data, setData] = useState<TaskQueueResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<StatusTab>("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    let alive = true;
    async function load(): Promise<void> {
      try {
        const body = await hiveGet<TaskQueueResponse>("dashboard/task-queue?limit=120");
        if (alive) {
          setData(body);
          setErr(null);
        }
      } catch (e) {
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Task queue unreachable";
        if (alive) {
          setErr(msg);
          setData(null);
        }
      }
    }
    void load();
    const id = window.setInterval(() => void load(), 45_000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  const filtered = useMemo(() => {
    if (!data) {
      return [];
    }
    const needle = q.trim().toLowerCase();
    return data.tasks.filter((t) => {
      if (!matchesTab(t, tab)) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        t.title.toLowerCase().includes(needle) ||
        t.short_id.toLowerCase().includes(needle) ||
        t.swarm_label.toLowerCase().includes(needle)
      );
    });
  }, [data, tab, q]);

  if (err) {
    return (
      <section
        id="hive-task"
        className="scroll-mt-24 rounded-3xl border border-danger/30 bg-danger/[0.06] p-6"
      >
        <p className="text-sm text-danger">Task queue: {err}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section id="hive-task" className="scroll-mt-24 space-y-4">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-white/10" />
        <div className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
        <div className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
      </section>
    );
  }

  return (
    <section id="hive-task" className="scroll-mt-24 flex flex-col gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#fafafa] md:text-3xl">
            Task Queue
          </h2>
          <p className="mt-2 font-[family-name:var(--font-inter)] text-sm text-zinc-500">
            {data.running_count} beží · {data.pending_count} čaká · {data.completed_today_count} dokončených dnes
          </p>
        </div>
        <Link
          href="/tasks/new"
          className="inline-flex items-center justify-center gap-2 rounded-2xl border-[2px] border-pollen bg-pollen px-5 py-3 font-[family-name:var(--font-poppins)] text-sm font-bold text-black shadow-[0_0_28px_rgb(255_184_0/0.42)] transition hover:bg-[#ffc933]"
        >
          <Plus className="h-4 w-4" aria-hidden />
          Nová úloha
        </Link>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", "Všetko"],
              ["running", "Beží"],
              ["pending", "Čaká"],
              ["completed", "Hotovo"],
            ] as const
          ).map(([key, label]) => {
            const active = tab === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={cn(
                  "rounded-full border px-3 py-1.5 font-[family-name:var(--font-inter)] text-xs font-semibold transition",
                  active
                    ? "border-white/15 bg-white/10 text-pollen"
                    : "border-transparent bg-black/40 text-zinc-500 hover:border-cyan/20 hover:text-zinc-300",
                )}
              >
                {label}
              </button>
            );
          })}
        </div>
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filtrovať úlohy…"
            className="w-full rounded-xl border border-white/10 bg-black/50 py-2.5 pl-10 pr-3 font-[family-name:var(--font-inter)] text-sm text-[#fafafa] outline-none placeholder:text-zinc-600 focus:border-pollen/35"
            aria-label="Filtrovať úlohy"
          />
        </div>
      </div>

      <ul className="flex flex-col gap-3">
        {filtered.length === 0 ? (
          <li className="rounded-2xl border border-dashed border-white/10 py-12 text-center font-[family-name:var(--font-inter)] text-sm text-zinc-500">
            Žiadne úlohy pre tento filter.
          </li>
        ) : (
          filtered.map((task) => {
            const { dot, label: stLabel } = statusDotAndLabel(task.status);
            const accent = laneAccent(task.lane);
            const fill = progressFillClass(task.lane, task.status);
            const pctText = progressPctTextClass(task.lane, task.status);
            return (
              <li
                key={task.id}
                className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0c12]/95 pl-1.5 pr-4 py-4 sm:pl-2 sm:pr-5"
              >
                <div className={cn("absolute bottom-0 left-0 top-0 w-1 rounded-l-2xl", accent)} aria-hidden />
                <div className="pl-3 sm:flex sm:items-stretch sm:justify-between sm:gap-6">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <h3 className="font-[family-name:var(--font-poppins)] text-base font-semibold text-[#fafafa]">
                        {task.title}
                      </h3>
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                        {task.short_id}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span
                        className={cn(
                          "rounded-full border px-2 py-0.5 font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-semibold uppercase tracking-wide",
                          swarmPillClass(task.lane),
                        )}
                      >
                        {task.swarm_label}
                      </span>
                      <span className="inline-flex items-center gap-1.5 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-400">
                        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
                        {stLabel}
                      </span>
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                        {task.steps_done}/{task.steps_total} krokov
                      </span>
                    </div>
                  </div>
                  <div className="mt-4 flex shrink-0 flex-col items-stretch sm:mt-0 sm:w-52 sm:items-end">
                    <p className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] font-semibold uppercase tracking-[0.14em] text-zinc-500 sm:text-right">
                      Progress
                    </p>
                    <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-black/60 sm:max-w-[13rem]">
                      <div className={cn("h-full rounded-full transition-all", fill)} style={{ width: `${task.progress_pct}%` }} />
                    </div>
                    <div className="mt-2 flex w-full items-center justify-between gap-3 sm:max-w-[13rem] sm:justify-end">
                      <span className={cn("font-[family-name:var(--font-jetbrains-mono)] text-sm font-bold", pctText)}>
                        {task.progress_pct}%
                      </span>
                      <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-zinc-500">
                        pred {formatQueueAgo(task.seconds_ago)}
                      </span>
                    </div>
                  </div>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </section>
  );
}
