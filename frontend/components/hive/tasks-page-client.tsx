"use client";

import dynamic from "next/dynamic";
import {
  Eye,
  GitBranch,
  LayoutGrid,
  List,
  Plus,
  RefreshCw,
  Shield,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState, useEffect } from "react";
import { toast } from "sonner";
import { useSearchParams } from "next/navigation";

import { usePlatform } from "@/components/hive/platform-context";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";
import { ResponsiveTable } from "@/components/ui/responsive-table";
import {
  V4Badge,
  V4BarRow,
  V4Card,
  V4CardHeader,
  V4Chip,
  type V4BadgeTone,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { hivePageShellError } from "@/lib/hive-page-error";
import { hiveMissionControlPageTitle } from "@/lib/hive-home-route";
import {
  AGENTS_HUB_PATH,
  EXECUTION_LANE_CROSS_LINK_LABELS,
  JOBS_PATH,
  TASKS_HUB_PATH,
  WORKFLOWS_PATH,
} from "@/lib/execution-lane-routes";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import { SIMULATIONS_ENABLED } from "@/lib/feature-flags";
import { cn } from "@/lib/utils";
import type { DashboardSummaryPayload, TaskQueueItem, TaskQueueResponse } from "@/lib/hive-types";
import { formatTimeAgoSeconds } from "@/lib/format-relative-time";

type FilterTab = "all" | "running" | "pending" | "done";
type ViewMode = "board" | "table";

const TaskResultDrawer = dynamic(
  () => import("@/components/hive/task-result-drawer").then((mod) => mod.TaskResultDrawer),
  { ssr: false },
);

const MissionKanbanPanel = dynamic(
  () => import("@/components/hive/mission-kanban-panel").then((mod) => mod.MissionKanbanPanel),
  {
    ssr: false,
    loading: () => (
      <HivePanelSectionSkeleton label="Loading mission kanban" minHeightClass="min-h-[24rem]" />
    ),
  },
);

const MissionHomePanel = dynamic(
  () => import("@/components/hive/mission-home-panel").then((mod) => mod.MissionHomePanel),
  {
    ssr: false,
    loading: () => (
      <HivePanelSectionSkeleton label="Loading Mission Home" minHeightClass="min-h-[12rem]" />
    ),
  },
);

const LANE_CARDS = [
  {
    href: "/tasks/new",
    title: "New task",
    description: "Compose and dispatch a mission into the hive queue.",
    icon: Plus,
  },
  {
    href: WORKFLOWS_PATH,
    title: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows,
    description: "Visual DAG execution, pause/resume, and run controls.",
    icon: GitBranch,
  },
  {
    href: JOBS_PATH,
    title: EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs,
    description: "Inspect async execution jobs, retries, and completion state.",
    icon: Zap,
  },
  {
    href: AGENTS_HUB_PATH,
    title: "Routines",
    description: "Manage supervisor routines and schedule-driven task execution.",
    icon: RefreshCw,
  },
  ...(SIMULATIONS_ENABLED
    ? [
        {
          href: "/simulations",
          title: "Simulations",
          description: "Verified simulation ledger and compliance snapshots.",
          icon: Shield,
        },
      ]
    : []),
] as const;

const TIER_ORDER = ["orchestrator", "manager", "worker", "scout", "unknown"] as const;

const TIER_LABELS: Record<string, string> = {
  orchestrator: "Queen",
  manager: "Managers",
  worker: "Workers",
  scout: "Scouts",
  unknown: "Unassigned",
};


function laneLabel(lane: string): string {
  if (!lane) return "Hive";
  return lane.charAt(0).toUpperCase() + lane.slice(1);
}

function displayStatus(
  status: string,
  progress: number,
): { label: string; tone: V4BadgeTone } {
  const s = status.toLowerCase();
  if (s === "running") return { label: "running", tone: "info" };
  if (s === "completed") return { label: "done", tone: "ok" };
  if (s === "failed" || s === "cancelled") return { label: "needs input", tone: "warn" };
  if (s === "pending" && progress > 0 && progress < 100) return { label: "needs input", tone: "warn" };
  if (s === "pending") return { label: "queued", tone: "gold" };
  return { label: s.replaceAll("_", " "), tone: "purple" };
}

function matchesFilter(task: TaskQueueItem, tab: FilterTab): boolean {
  const s = task.status.toLowerCase();
  if (tab === "all") return true;
  if (tab === "running") return s === "running";
  if (tab === "pending") return s === "pending";
  if (tab === "done") return s === "completed";
  return true;
}

function buildTierRows(summary: DashboardSummaryPayload | null): { label: string; count: number; pct: number }[] {
  const tiers = summary?.agents.by_hive_tier ?? {};
  const total = summary?.agents.total ?? 0;
  const ordered = [
    ...TIER_ORDER.filter((key) => key in tiers),
    ...Object.keys(tiers).filter((key) => !TIER_ORDER.includes(key as (typeof TIER_ORDER)[number])),
  ];
  return ordered.map((key) => {
    const count = tiers[key] ?? 0;
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    return {
      label: TIER_LABELS[key] ?? key,
      count,
      pct,
    };
  });
}

export function TasksPageClient() {
  const { soloMode, personalOsMode } = usePlatform();
  const pageTitle = hiveMissionControlPageTitle({ soloMode });
  const [queue, setQueue] = useState<TaskQueueResponse | null>(null);
  const [summary, setSummary] = useState<DashboardSummaryPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<FilterTab>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("board");
  const filterScrollRef = useCenterActiveInScrollRow(filter);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [drawerEdit, setDrawerEdit] = useState(false);
  const [kanbanRefresh, setKanbanRefresh] = useState(0);
  const searchParams = useSearchParams();

  const openTask = useCallback((taskId: string, opts?: { edit?: boolean }) => {
    setSelectedTaskId(taskId);
    setDrawerEdit(opts?.edit ?? false);
  }, []);

  useEffect(() => {
    const taskParam = searchParams.get("task");
    if (taskParam) {
      setSelectedTaskId(taskParam);
      setDrawerEdit(false);
    }
  }, [searchParams]);

  const reload = useCallback(async () => {
    try {
      const [queuePayload, summaryPayload] = await Promise.all([
        hiveGet<TaskQueueResponse>("dashboard/task-queue?limit=100"),
        hiveGet<DashboardSummaryPayload>("dashboard/summary"),
      ]);
      setQueue(queuePayload);
      setSummary(summaryPayload);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Task queue unreachable";
      setErr(msg);
    }
  }, []);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  async function syncNow() {
    setBusy(true);
    try {
      await reload();
      toast.success("Task queue synced");
    } finally {
      setBusy(false);
    }
  }

  const tasks = useMemo(() => queue?.tasks ?? [], [queue?.tasks]);
  const activeCount = (queue?.running_count ?? 0) + (queue?.pending_count ?? 0);

  const filteredTasks = useMemo(() => tasks.filter((task) => matchesFilter(task, filter)), [tasks, filter]);

  const tierRows = buildTierRows(summary);
  const recentTasks = tasks.slice(0, 6);

  const filterCounts = useMemo(
    () => ({
      all: tasks.length,
      running: tasks.filter((t) => matchesFilter(t, "running")).length,
      pending: tasks.filter((t) => matchesFilter(t, "pending")).length,
      done: tasks.filter((t) => matchesFilter(t, "done")).length,
    }),
    [tasks],
  );

  const topLanes = LANE_CARDS.slice(0, 3);
  const bottomLanes = LANE_CARDS.slice(3);

  if (!queue) {
    return (
      <HivePageShell
        title={pageTitle}
        subtitle="Mission queue · workflows · async jobs"
        hintKey="tasks"
        error={hivePageShellError(err, () => setErr(null))}
      >
        <HivePanelSectionSkeleton label="Loading task queue" minHeightClass="min-h-[20rem]" />
      </HivePageShell>
    );
  }

  return (
    <HivePageShell
      canvasClassName="gap-6"
      title={pageTitle}
      subtitle={
        <>
          <span className="text-(--qs-text-2)">{activeCount} active</span>
          {" · "}
          <span>{queue?.pending_count ?? 0} pending</span>
          {" · "}
          <span>{queue?.completed_today_count ?? 0} completed today</span>
          {" · "}
          <span className="text-data">Mission Kanban</span>
        </>
      }
      hintKey="tasks"
      error={hivePageShellError(err, () => setErr(null))}
      status={
        <div className="flex items-center gap-2">
          <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm hidden gap-1.5 lg:inline-flex">
            <Plus className="h-3.5 w-3.5" aria-hidden />
            New task
          </Link>
          <div className="hidden gap-1 lg:flex">
            <button
              type="button"
              className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1.5", viewMode === "board" && "border-pollen/40 text-pollen")}
              onClick={() => setViewMode("board")}
            >
              <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
              Board
            </button>
            <button
              type="button"
              className={cn("qs-btn qs-btn--ghost qs-btn--sm gap-1.5", viewMode === "table" && "border-pollen/40 text-pollen")}
              onClick={() => setViewMode("table")}
            >
              <List className="h-3.5 w-3.5" aria-hidden />
              Table
            </button>
          </div>
          <HiveRefreshButton busy={busy} label="Sync" onClick={() => void syncNow()} />
        </div>
      }
    >
      {!personalOsMode ? <HubEcosystemStrip preset="tasks" /> : null}

      {soloMode && viewMode === "board" ? <MissionHomePanel /> : null}

      {viewMode === "board" ? (
        <MissionKanbanPanel onOpenTask={openTask} refreshSignal={kanbanRefresh} />
      ) : null}

      {viewMode === "table" ? (
        <>

      <div className="v4-mobile-card-slider v4-mobile-card-slider--cols-3">
        {topLanes.map((lane) => {
          const Icon = lane.icon;
          return (
            <Link key={lane.href} href={lane.href} className="v4-lane-card">
              <span className="v4-lane-card-icon">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold text-(--qs-text)">{lane.title}</span>
                <span className="mt-0.5 block text-xs text-(--qs-text-3)">{lane.description}</span>
              </span>
            </Link>
          );
        })}
      </div>

      {bottomLanes.length ? (
        <div className="v4-mobile-card-slider">
          {bottomLanes.map((lane) => {
            const Icon = lane.icon;
            return (
              <Link key={lane.href} href={lane.href} className="v4-lane-card">
                <span className="v4-lane-card-icon">
                  <Icon className="h-4 w-4" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-(--qs-text)">{lane.title}</span>
                  <span className="mt-0.5 block text-xs text-(--qs-text-3)">{lane.description}</span>
                </span>
              </Link>
            );
          })}
        </div>
      ) : null}

      <V4Card>
        <div className="mb-3 flex flex-col gap-3">
          <div ref={filterScrollRef} className="v4-chip-scroll">
            <V4Chip active={filter === "all"} count={filterCounts.all} onClick={() => setFilter("all")}>
              All
            </V4Chip>
            <V4Chip active={filter === "running"} count={filterCounts.running} onClick={() => setFilter("running")}>
              Running
            </V4Chip>
            <V4Chip active={filter === "pending"} count={filterCounts.pending} onClick={() => setFilter("pending")}>
              Pending
            </V4Chip>
            <V4Chip active={filter === "done"} count={filterCounts.done} onClick={() => setFilter("done")}>
              Done
            </V4Chip>
          </div>
          <Link href="/tasks/new" className="qs-btn qs-btn--ghost qs-btn--sm w-full justify-center gap-2">
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            New task
          </Link>
        </div>
        <ResponsiveTable
          table={
            <table className="v4-data-table min-w-[920px]">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Swarm</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Updated</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {!filteredTasks.length ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-sm text-(--qs-text-3)">
                      {tasks.length ? "No tasks match this filter." : "No tasks yet — create one with New task."}
                    </td>
                  </tr>
                ) : (
                  filteredTasks.map((task) => {
                    const status = displayStatus(task.status, task.progress_pct);
                    return (
                      <tr key={task.id}>
                        <td>
                          <div className="v4-task-name">{task.title}</div>
                          <div className="v4-task-id">{task.short_id}</div>
                        </td>
                        <td>
                          <V4Badge tone="purple">{laneLabel(task.lane)}</V4Badge>
                        </td>
                        <td>
                          <V4Badge tone={status.tone}>{status.label}</V4Badge>
                        </td>
                        <td>
                          <div className="v4-progress-cell">
                            <div className="v4-progress-track">
                              <div className="v4-progress-fill" style={{ width: `${task.progress_pct}%` }} />
                            </div>
                            <span className="v4-progress-pct">{task.progress_pct}%</span>
                          </div>
                        </td>
                        <td className="text-(--qs-text-3)">{formatTimeAgoSeconds(task.seconds_ago)}</td>
                        <td>
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                            onClick={() => setSelectedTaskId(task.id)}
                          >
                            <Eye className="h-3.5 w-3.5" aria-hidden />
                            View
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          }
          cards={
            !filteredTasks.length ? (
              <p className="py-8 text-center text-sm text-(--qs-text-3)">
                {tasks.length ? "No tasks match this filter." : "No tasks yet — create one with New task."}
              </p>
            ) : (
              filteredTasks.map((task) => {
                const status = displayStatus(task.status, task.progress_pct);
                return (
                  <article key={task.id} className="v4-mobile-card-row">
                    <div className="v4-mobile-card-row__head">
                      <div className="min-w-0">
                        <div className="v4-task-name">{task.title}</div>
                        <div className="v4-task-id">{task.short_id}</div>
                      </div>
                      <V4Badge tone={status.tone}>{status.label}</V4Badge>
                    </div>
                    <div className="v4-mobile-card-row__meta">
                      <V4Badge tone="purple">{laneLabel(task.lane)}</V4Badge>
                      <span>{formatTimeAgoSeconds(task.seconds_ago)}</span>
                    </div>
                    <div className="v4-progress-cell">
                      <div className="v4-progress-track">
                        <div className="v4-progress-fill" style={{ width: `${task.progress_pct}%` }} />
                      </div>
                      <span className="v4-progress-pct">{task.progress_pct}%</span>
                    </div>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm w-full gap-1.5"
                      onClick={() => setSelectedTaskId(task.id)}
                    >
                      <Eye className="h-3.5 w-3.5" aria-hidden />
                      View task
                    </button>
                  </article>
                );
              })
            )
          }
        />
      </V4Card>

      <div className="v4-cols-2">
        <V4Card>
          <V4CardHeader
            title="Performance by tier"
            description="Share of agents in the hive · API summary"
            hint={sectionHintNode("tasksPerformanceTier")}
          />
          {tierRows.length ? (
            tierRows.map((row) => (
              <V4BarRow
                key={row.label}
                label={row.label}
                value={`${row.pct}% · ${row.count}`}
                pct={row.pct}
              />
            ))
          ) : (
            <p className="text-sm text-(--qs-text-3)">Agent tier data loading…</p>
          )}
        </V4Card>

        <V4Card>
          <V4CardHeader
            title="Recent tasks"
            description="Latest 6 rows from /api/v1/tasks"
            hint={sectionHintNode("tasksRecent")}
          />
          <div className="flex flex-col gap-3">
            {!recentTasks.length ? (
              <p className="text-sm text-(--qs-text-3)">No recent tasks.</p>
            ) : (
              recentTasks.map((task) => {
                const status = displayStatus(task.status, task.progress_pct);
                return (
                  <div key={task.id} className="v4-recent-task-row">
                    <V4Badge tone={status.tone}>{status.label}</V4Badge>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-(--qs-text)">{task.title}</div>
                      <div className="mt-0.5 text-xs text-(--qs-text-3)">
                        {task.short_id} · {laneLabel(task.lane)} · {formatTimeAgoSeconds(task.seconds_ago)}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
                      onClick={() => setSelectedTaskId(task.id)}
                    >
                      View
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </V4Card>
      </div>
        </>
      ) : null}

      <TaskResultDrawer
        onClose={() => {
          setSelectedTaskId(null);
          setDrawerEdit(false);
        }}
        taskId={selectedTaskId}
        initialEdit={drawerEdit}
        onMutated={() => setKanbanRefresh((value) => value + 1)}
      />
    </HivePageShell>
  );
}
