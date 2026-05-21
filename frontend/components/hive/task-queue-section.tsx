"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { useCockpitTelemetry } from "@/components/hive/cockpit-telemetry-provider";
import { V4Badge, V4Card, V4CardHeader, V4Chip, V4SearchInput } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { cockpitSwrKeys } from "@/lib/cockpit-swr-keys";
import { COCKPIT_POLL_TASK_QUEUE_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
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

function swarmBadgeTone(lane: string): "info" | "gold" | "warn" | "ok" {
  const L = lane.toLowerCase();
  if (L === "scout") {
    return "info";
  }
  if (L === "eval") {
    return "gold";
  }
  if (L === "sim") {
    return "warn";
  }
  return "ok";
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
  const { wsConnected } = useCockpitTelemetry();
  const pollMs = wsConnected
    ? Math.max(COCKPIT_PERF.wsConnectedPollMs, COCKPIT_POLL_TASK_QUEUE_MS)
    : COCKPIT_POLL_TASK_QUEUE_MS;
  const pollOptions = useSwrVisiblePollOptions(pollMs);
  const { data, error } = useSWR<TaskQueueResponse>(
    cockpitSwrKeys.taskQueue(120),
    () => hiveGet<TaskQueueResponse>("dashboard/task-queue?limit=120"),
    {
      ...pollOptions,
      keepPreviousData: true,
      dedupingInterval: 12_000,
    },
  );
  const err = error instanceof Error ? error.message : error ? "Task queue unreachable" : null;
  const [tab, setTab] = useState<StatusTab>("all");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    if (!data) {
      return [];
    }
    const needle = q.trim().toLowerCase();
    return (data.tasks ?? []).filter((t) => {
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
      <V4Card id="hive-task" className="scroll-mt-24 border-danger/30 bg-danger/[0.06]">
        <p className="text-sm text-danger">Task queue: {err}</p>
      </V4Card>
    );
  }

  if (!data) {
    return (
      <V4Card id="hive-task" className="scroll-mt-24 v4-card-interactive">
        <div className="h-10 w-56 animate-pulse rounded-lg bg-white/10" />
        <div className="mt-4 h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
        <div className="mt-3 h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
      </V4Card>
    );
  }

  return (
    <V4Card id="hive-task" className="scroll-mt-24 v4-card-interactive">
      <V4CardHeader
        title="Task queue"
        description={`${data.running_count} running · ${data.pending_count} queued · ${data.completed_today_count} completed today`}
      />

      <div className="v4-task-queue-controls mt-5 flex flex-col gap-3">
        <div className="v4-chip-scroll">
          {(
            [
              ["all", "All"],
              ["running", "Running"],
              ["pending", "Queued"],
              ["completed", "Done"],
            ] as const
          ).map(([key, label]) => (
            <V4Chip key={key} active={tab === key} onClick={() => setTab(key)}>
              {label}
            </V4Chip>
          ))}
        </div>
        <Link href="/tasks/new" className="qs-btn qs-btn--primary qs-btn--sm w-full justify-center gap-2">
          <Plus className="h-4 w-4 shrink-0" aria-hidden />
          New task
        </Link>
        <V4SearchInput
          value={q}
          onChange={setQ}
          placeholder="Filter tasks…"
          aria-label="Filter tasks"
          className="w-full"
        />
      </div>

      <ul className="mt-5 flex flex-col gap-3">
        {filtered.length === 0 ? (
          <li className="v4-empty py-12 text-sm">No tasks match this filter.</li>
        ) : (
          filtered.map((task) => {
            const { dot, label: stLabel } = statusDotAndLabel(task.status);
            const accent = laneAccent(task.lane);
            const fill = progressFillClass(task.lane, task.status);
            const pctText = progressPctTextClass(task.lane, task.status);
            return (
              <li key={task.id} className="v4-list-row">
                <div className={cn("v4-list-row-accent", accent)} aria-hidden />
                <div className="pl-3 sm:flex sm:items-stretch sm:justify-between sm:gap-6">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <h3 className="text-base font-semibold text-(--qs-text)">{task.title}</h3>
                      <span className="text-[11px] tracking-tight text-(--qs-text-3)">{task.short_id}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <V4Badge tone={swarmBadgeTone(task.lane)}>{task.swarm_label}</V4Badge>
                      <span className="inline-flex items-center gap-1.5 text-[11px] text-(--qs-text-3)">
                        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
                        {stLabel}
                      </span>
                      <span className="text-[11px] tabular-nums text-(--qs-text-3)">
                        {task.steps_done}/{task.steps_total} krokov
                      </span>
                    </div>
                  </div>
                  <div className="mt-4 flex shrink-0 flex-col items-stretch sm:mt-0 sm:w-52 sm:items-end">
                    <p className="v4-label-kicker text-(--qs-text-3) sm:text-right">Progress</p>
                    <div className="v4-bar-track mt-1.5 sm:max-w-[13rem]">
                      <div className={cn("v4-bar-fill", fill)} style={{ width: `${task.progress_pct}%` }} />
                    </div>
                    <div className="mt-2 flex w-full items-center justify-between gap-3 sm:max-w-[13rem] sm:justify-end">
                      <span className={cn("text-sm font-bold tabular-nums", pctText)}>{task.progress_pct}%</span>
                      <span className="text-[11px] text-(--qs-text-3)">pred {formatQueueAgo(task.seconds_ago)}</span>
                    </div>
                  </div>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </V4Card>
  );
}
