"use client";

import Link from "next/link";
import { Plus, RefreshCw } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";

import { RoutineCatalogCard } from "@/components/hive/routine-catalog-card";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4Card, V4CardHeader, V4Chip, V4Stat, V4IconAgents, V4IconBolt } from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import type { SupervisorControlSummaryRow, SupervisorRoutineRow } from "@/lib/hive-types";
import { ROUTINES_CROSS_LINK_LABELS, ROUTINES_PATH } from "@/lib/routines-routes";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

type RoutineFilter = "all" | "active" | "paused" | "errors";

const ROUTINE_FILTERS: { id: RoutineFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "active", label: "Active" },
  { id: "paused", label: "Paused" },
  { id: "errors", label: "Errors" },
];

function matchesFilter(row: SupervisorRoutineRow, filter: RoutineFilter): boolean {
  if (filter === "active") {
    return row.is_active;
  }
  if (filter === "paused") {
    return !row.is_active;
  }
  if (filter === "errors") {
    return Boolean(row.last_error?.trim()) || row.status === "error" || row.status === "failed";
  }
  return true;
}

/** Supervisor routines hub — catalog cards, create form, webhook ingress. */
export function RoutinesPageClient(): JSX.Element {
  const [filter, setFilter] = useState<RoutineFilter>("all");
  const [routineName, setRoutineName] = useState("");
  const [routineGoal, setRoutineGoal] = useState("");
  const [routineInterval, setRoutineInterval] = useState(3600);
  const [createBusy, setCreateBusy] = useState(false);
  const [triggerBusyId, setTriggerBusyId] = useState<string | null>(null);

  const poll = useRouteScopedPollOptions(COCKPIT_POLL_BOARD_MS * 1.5, ROUTINES_PATH);

  const { data: rawRoutines = [], mutate: mutateRoutines, isLoading } = useSWR<SupervisorRoutineRow[]>(
    "hive/routines-page",
    () => hiveGet<SupervisorRoutineRow[]>("agents/routines?limit=120"),
    poll,
  );
  const routines = Array.isArray(rawRoutines) ? rawRoutines : [];

  const { data: summary, mutate: mutateSummary } = useSWR<SupervisorControlSummaryRow>(
    "hive/routines-page-summary",
    () => hiveGet<SupervisorControlSummaryRow>("agents/sessions/summary"),
    poll,
  );

  const filterCounts = useMemo(
    () => ({
      all: routines.length,
      active: routines.filter((r) => r.is_active).length,
      paused: routines.filter((r) => !r.is_active).length,
      errors: routines.filter((r) => matchesFilter(r, "errors")).length,
    }),
    [routines],
  );

  const visibleRoutines = useMemo(
    () => routines.filter((row) => matchesFilter(row, filter)),
    [routines, filter],
  );

  const pageSize = useGridTwoRowPageSize();
  const pagination = usePaginatedSlice(visibleRoutines, pageSize, `${filter}|${pageSize}|${routines.length}`);

  const createRoutine = useCallback(async (): Promise<void> => {
    if (routineName.trim().length < 2 || routineGoal.trim().length < 4) {
      toast.error("Routine name and goal template are too short.");
      return;
    }
    setCreateBusy(true);
    try {
      await hivePostJson("agents/routines", {
        name: routineName.trim(),
        goal_template: routineGoal.trim(),
        schedule_kind: "interval",
        interval_seconds: Math.max(60, routineInterval),
        runtime_mode: "durable",
        roles: ["researcher", "critic"],
        retrieval_contract: "customer_history+policy+last_3_tasks",
        skills: ["context", "diagnose"],
      });
      setRoutineName("");
      setRoutineGoal("");
      setRoutineInterval(3600);
      await Promise.all([mutateRoutines(), mutateSummary()]);
      toast.success("Routine created.");
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Routine create failed";
      toast.error(msg);
    } finally {
      setCreateBusy(false);
    }
  }, [routineGoal, routineInterval, routineName, mutateRoutines, mutateSummary]);

  const triggerRoutine = useCallback(
    async (routineId: string): Promise<void> => {
      setTriggerBusyId(routineId);
      try {
        await hivePostJson(`agents/routines/${routineId}/trigger`, {});
        toast.success("Routine triggered.");
        await Promise.all([mutateRoutines(), mutateSummary()]);
      } catch (e) {
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Routine trigger failed";
        toast.error(msg);
      } finally {
        setTriggerBusyId(null);
      }
    },
    [mutateRoutines, mutateSummary],
  );

  return (
    <HivePageShell
      title="Routines"
      subtitle="Recurring supervisor sessions · Celery schedule tick · webhook ingress (L4)"
      hintKey="routines"
      actions={
        <Link href="/recipes" className="qs-btn qs-btn--ghost qs-btn--sm">
          {ROUTINES_CROSS_LINK_LABELS.openRecipes}
        </Link>
      }
    >
      <HubEcosystemStrip preset="routines" />

      <div className="v4-stat-grid">
        <V4Stat label="Routines total" value={summary?.routines_total ?? routines.length} icon={V4IconAgents} iconTone="purple" />
        <V4Stat
          label="Active"
          value={summary?.active_routines ?? filterCounts.active}
          icon={RefreshCw}
          iconTone="cyan"
          valueVariant="text"
        />
        <V4Stat
          label="Due now"
          value={summary?.due_routines ?? 0}
          icon={V4IconBolt}
          iconTone="green"
          valueVariant="text"
        />
      </div>

      <V4Card>
        <V4CardHeader
          kicker="New routine"
          title="Create supervisor routine"
          description="Interval schedule — durable runtime with researcher + critic roles."
          actions={
            <V4Badge tone="gold">
              {filterCounts.active} active
            </V4Badge>
          }
        />
        <div className="v4-routines-form grid gap-3">
          <input
            className="qs-input w-full min-w-0"
            placeholder="Routine name"
            value={routineName}
            onChange={(event) => setRoutineName(event.target.value)}
          />
          <input
            className="qs-input w-full min-w-0"
            placeholder="Goal template"
            value={routineGoal}
            onChange={(event) => setRoutineGoal(event.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <input
              className="qs-input w-full min-w-0"
              type="number"
              min={60}
              step={60}
              aria-label="Interval seconds"
              value={routineInterval}
              onChange={(event) => setRoutineInterval(Number(event.target.value || 3600))}
            />
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm w-full justify-center gap-2 sm:w-auto"
              disabled={createBusy}
              onClick={() => void createRoutine()}
            >
              <Plus className="h-4 w-4 shrink-0" aria-hidden />
              {createBusy ? "Creating…" : "Create routine"}
            </button>
          </div>
        </div>
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Routine catalog"
          description="YouTube / RSS / API · periodicity · HiveMind ingest · auto-spawn rules."
          actions={
            <div className="v4-chip-scroll v4-foragers-filter-chips">
              {ROUTINE_FILTERS.map((tab) => (
                <V4Chip
                  key={tab.id}
                  active={filter === tab.id}
                  count={filterCounts[tab.id]}
                  onClick={() => setFilter(tab.id)}
                >
                  {tab.label}
                </V4Chip>
              ))}
            </div>
          }
        />

        {isLoading ? (
          <div className="hub-catalog-grid">
            {Array.from({ length: 4 }, (_, index) => (
              <article key={`routine-skel-${index}`} className="hub-catalog-card animate-pulse" aria-hidden>
                <div className="h-4 w-40 rounded bg-white/15" />
                <div className="mt-3 h-3 w-full rounded bg-white/10" />
                <div className="mt-2 h-16 w-full rounded bg-white/10" />
              </article>
            ))}
          </div>
        ) : visibleRoutines.length === 0 ? (
          <p className="text-sm text-(--qs-text-3)">
            {routines.length
              ? "No routines match this filter."
              : "No routines yet — create one above or schedule from a verified recipe."}
          </p>
        ) : (
          <ViewportBoundedPanel
            className={cn("v4-recipe-catalog-panel v4-marketplace-shell--paginated border-0 bg-transparent shadow-none")}
            footer={
              <ListPaginator
                page={pagination.page}
                totalPages={pagination.totalPages}
                totalItems={pagination.totalItems}
                pageSize={pageSize}
                onPageChange={pagination.setPage}
              />
            }
          >
            <div className="hub-catalog-grid">
              {pagination.slice.map((routine, idx) => (
                <RoutineCatalogCard
                  key={routine.id}
                  routine={routine}
                  index={(pagination.page - 1) * pageSize + idx}
                  triggerBusy={triggerBusyId === routine.id}
                  onTrigger={(id) => void triggerRoutine(id)}
                />
              ))}
            </div>
          </ViewportBoundedPanel>
        )}
      </V4Card>
    </HivePageShell>
  );
}
