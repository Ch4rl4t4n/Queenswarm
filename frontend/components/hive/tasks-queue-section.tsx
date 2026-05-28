"use client";

import Link from "next/link";
import { useState } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import type { TaskRow } from "@/lib/hive-types";
import type { TaskCounts } from "@/lib/tasks-queue-utils";
import { cn } from "@/lib/utils";

type TaskBucket = "all" | "running" | "pending" | "completed";

interface TasksQueueSectionProps {
  tasks: TaskRow[];
}

function classifyStatus(status: string): Exclude<TaskBucket, "all"> {
  const u = status.toUpperCase();
  if (u.includes("COMPLETE") || u.includes("DONE") || u.includes("SUCCESS")) return "completed";
  if (u.includes("RUN") || u.includes("ACTIVE") || u.includes("PROCESS") || u.includes("BUSY")) return "running";
  return "pending";
}

function laneAccentClass(taskType: string, swarmId: string | null | undefined, bucket: TaskBucket): string {
  const hay = `${taskType} ${swarmId ?? ""}`.toUpperCase();
  if (hay.includes("ACTION") || hay.includes("EXEC")) return "bg-success";
  if (hay.includes("EVAL")) return "bg-pollen";
  if (hay.includes("SIM")) return "bg-alert";
  if (hay.includes("SCOUT")) return "bg-data";
  if (bucket === "completed") return "bg-data";
  if (bucket === "pending") return "bg-pollen";
  return "bg-success";
}

function progressHueClass(taskType: string, swarmId: string | null | undefined, bucket: TaskBucket): string {
  const s = laneAccentClass(taskType, swarmId, bucket);
  if (s.includes("pollen")) return "text-pollen";
  if (s.includes("success")) return "text-success";
  if (s.includes("alert")) return "text-alert";
  return "text-data";
}

function statusBadge(bucket: Exclude<TaskBucket, "all">): string {
  if (bucket === "running") return "border-success/40 text-success bg-success/[0.08]";
  if (bucket === "pending") return "border-pollen/40 text-pollen bg-pollen/[0.06]";
  return "border-data/40 text-data bg-data/[0.08]";
}

function pctFor(id: string, bucket: Exclude<TaskBucket, "all">): number {
  let h = 0;
  for (let i = 0; i < id.length; i += 1) h += id.charCodeAt(i);
  if (bucket === "completed") return 100;
  if (bucket === "pending") return Math.min(((h >> 3) % 40) + 5, 40);
  return Math.min((((h >> 5) || 53) % 70) + 15, 95);
}

interface TasksQueueHeaderStatsProps {
  counts: TaskCounts;
}

export function TasksQueueHeaderStats({ counts }: TasksQueueHeaderStatsProps) {
  return (
    <span className="font-[family-name:var(--font-poppins)] text-sm text-muted-foreground">
      <span className="text-[#fafafa]/90">{counts.running + counts.pending}</span> active · {counts.pending} pending ·{" "}
      <span>{counts.completed}</span> completed today
    </span>
  );
}

/** Task queue cockpit — buckets, filter capsule, swarm accent strips. */
export function TasksQueueSection({ tasks }: TasksQueueSectionProps) {
  const [bucket, setBucket] = useState<TaskBucket>("all");
  const [needle, setNeedle] = useState("");

  const filtered = tasks.filter((t) => {
    const bClass = classifyStatus(t.status);
    const inBucket = bucket === "all" ? true : bClass === bucket;
    const q = needle.trim().toLowerCase();
    const hay = `${t.title} ${t.id} ${t.task_type}`.toLowerCase();
    return inBucket && (q === "" || hay.includes(q));
  });

  const tabBtn = (id: TaskBucket, label: string) => (
    <button
      key={id}
      type="button"
      onClick={() => setBucket(id)}
      className={cn(
        "shrink-0 rounded-full px-3 py-1.5 font-[family-name:var(--font-poppins)] text-xs font-medium transition whitespace-nowrap",
        bucket === id ? "border border-transparent bg-black/65 text-[#fafafa]" : "border border-transparent text-zinc-500 hover:text-pollen",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 border-b border-[color:var(--qs-border-2)]/[0.08] pb-5 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between sm:gap-6">
        <div className="flex w-full min-w-0 items-center gap-2 sm:w-auto">
          <div className="flex min-w-0 gap-1 overflow-x-auto rounded-full bg-black/40 p-1 ring-1 ring-cyan/[0.1] hive-scrollbar pb-px sm:overflow-visible">
            {tabBtn("all", "All")}
            {tabBtn("running", "Running")}
            {tabBtn("pending", "Pending")}
            {tabBtn("completed", "Completed")}
          </div>
          <InfoHint
            title="Task status filter"
            description="Switches task visibility based on execution pipeline status."
            options={["All", "Running", "Pending", "Completed"]}
          />
        </div>
        <div className="flex w-full min-w-0 items-center gap-2 sm:w-auto">
          <input
            type="search"
            value={needle}
            onChange={(e) => setNeedle(e.target.value)}
            placeholder="Filter tasks…"
            className="w-full min-w-0 max-w-full rounded-xl border border-[color:var(--qs-border)] bg-black/45 px-4 py-2 font-(family-name:--font-poppins) text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none sm:max-w-[320px] sm:flex-none"
          />
          <InfoHint
            title="Task search"
            description="Filters by task title, ID, and task type."
            options={["Live filter", "Search title", "Search task type"]}
          />
        </div>
      </div>

      <div className="space-y-3">
        {filtered.map((t) => {
          const b = classifyStatus(t.status);
          const pct = pctFor(t.id, b);
          const strip = laneAccentClass(t.task_type, t.swarm_id, b);
          return (
            <article
              key={t.id}
              className="relative flex flex-col gap-4 overflow-hidden rounded-2xl border border-[color:var(--qs-border-2)]/[0.08] bg-hive-card/90 p-4 sm:flex-row sm:items-center sm:justify-between lg:p-5"
            >
              <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1 rounded-l-2xl", strip)} />
              <div className="min-w-0 pt-1 pl-3">
                <p className="font-[family-name:var(--font-poppins)] font-semibold tracking-tight text-[#fafafa]">
                  {t.title}{" "}
                  <span className="font-[family-name:var(--font-poppins)] text-[11px] font-normal lowercase text-zinc-500">
                    {t.id}
                  </span>
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
                  <span className="rounded-full border border-[color:var(--qs-border)] px-2 py-0.5 font-[family-name:var(--font-poppins)] uppercase tracking-[0.08em]">
                    swarm · {t.task_type}
                  </span>
                  <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5", statusBadge(b))}>
                    ● {t.status.replaceAll("_", " ")}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1 pl-3 sm:w-[210px]">
                <span className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.22em] text-zinc-500">
                  Progress
                </span>
                <p className={cn("font-[family-name:var(--font-poppins)] text-2xl tabular-nums", progressHueClass(t.task_type, t.swarm_id, b))}>{pct}%</p>
                <div className="h-2 w-full max-w-[200px] rounded-full bg-black/50">
                  <div className={cn("h-full rounded-full opacity-90", strip)} style={{ width: `${pct}%` }} />
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {filtered.length === 0 ? (
        <p className="text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-500">No tasks in this filter.</p>
      ) : null}
    </div>
  );
}

export function TasksNewTaskActions() {
  return (
    <div className="flex items-center gap-2">
      <Link href="/tasks/new" className="qs-btn qs-btn--primary">
        + New task
      </Link>
      <InfoHint
        title="New task"
        description="Creates a new task in the execution queue."
        options={["Define title", "Set task type", "Assign mission scope"]}
      />
    </div>
  );
}
