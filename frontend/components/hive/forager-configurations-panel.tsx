"use client";

import { FileText, ListTodo, Pencil, Play, Trash2 } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ForagerProgressCell } from "@/components/hive/forager-progress-cell";
import { ForagerResultsDialog } from "@/components/hive/forager-results-dialog";
import { HiveSwitch } from "@/components/ui/hive-switch";
import { QsSelect } from "@/components/ui/qs-select";
import { V4Badge, type V4BadgeTone } from "@/components/ui/v4";
import { HiveApiError, hivePatchJson, hivePostJson } from "@/lib/api";
import { formatTimeAgoSeconds } from "@/lib/format-relative-time";
import { foragerKnowledgeHref } from "@/lib/execution-lane-routes";
import type {
  ForagerRow,
  ForagersOverviewConfiguration,
  ForagersSpawnPolicy,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type StatusFilter = "all" | ForagersOverviewConfiguration["status"];

const FORAGER_CONFIG_PREVIEW_LIMIT = 3;

export interface ForagerConfigurationsPanelProps {
  configurations: ForagersOverviewConfiguration[];
  foragersById: Map<string, ForagerRow>;
  policy: ForagersSpawnPolicy;
  canManage: boolean;
  busy: string | null;
  onPolicyChange: (policy: ForagersSpawnPolicy) => void;
  onReload: () => Promise<void>;
  onRun: (id: string) => Promise<void>;
  onPromoteTask: (row: ForagersOverviewConfiguration) => Promise<void>;
  onEdit: (id: string) => void;
  onDelete: (row: ForagersOverviewConfiguration) => void;
  onToggleActive: (row: ForagersOverviewConfiguration, enabled: boolean) => Promise<void>;
}

function shortForagerId(id: string): string {
  return `F-${id.replace(/-/g, "").slice(0, 4).toUpperCase()}`;
}

function statusTone(status: ForagersOverviewConfiguration["status"]): V4BadgeTone {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  if (status === "error") return "err";
  return "purple";
}

function statusLabel(status: ForagersOverviewConfiguration["status"]): string {
  if (status === "ok") return "active";
  if (status === "warn") return "needs input";
  return status;
}

function isForagerSessionLive(row: ForagersOverviewConfiguration): boolean {
  return row.progress_kind === "live_run";
}

function ForagerSkillBadge({ slug }: { slug: string }): JSX.Element {
  return (
    <span className="inline-flex max-w-full items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-(family-name:--font-jetbrains-mono) text-[10px] text-emerald-200">
      {slug}
    </span>
  );
}

function ForagerConfigurationsPanelInner({
  configurations,
  foragersById,
  policy,
  canManage,
  busy,
  onPolicyChange,
  onReload,
  onRun,
  onPromoteTask,
  onEdit,
  onDelete,
  onToggleActive,
}: ForagerConfigurationsPanelProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [showAllConfigurations, setShowAllConfigurations] = useState(false);
  const [resultsForager, setResultsForager] = useState<{ id: string; name: string } | null>(null);
  const [autoApproveBusy, setAutoApproveBusy] = useState(false);
  const [pauseAllBusy, setPauseAllBusy] = useState(false);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return configurations.filter((row) => {
      if (statusFilter !== "all" && row.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      const forager = foragersById.get(row.id);
      const haystack = [
        row.source_name,
        row.source_type,
        row.schedule_label,
        row.status,
        forager?.description ?? "",
        ...(forager?.tools ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [configurations, foragersById, query, statusFilter]);

  const visibleRows = useMemo(() => {
    if (showAllConfigurations) {
      return filteredRows;
    }
    return filteredRows.slice(0, FORAGER_CONFIG_PREVIEW_LIMIT);
  }, [filteredRows, showAllConfigurations]);

  const hiddenConfigurationCount = Math.max(0, filteredRows.length - FORAGER_CONFIG_PREVIEW_LIMIT);

  const openResults = useCallback((row: ForagersOverviewConfiguration) => {
    setResultsForager({ id: row.id, name: row.source_name });
  }, []);

  const resultsReportReady = useCallback((row: ForagersOverviewConfiguration): boolean => {
    return (row.run_progress_pct ?? 0) >= 100 && row.status === "ok";
  }, []);

  useEffect(() => {
    setShowAllConfigurations(false);
  }, [query, statusFilter, configurations.length]);

  const patchAutoApprove = useCallback(
    async (enabled: boolean) => {
      setAutoApproveBusy(true);
      try {
        const updated = await hivePatchJson<ForagersSpawnPolicy>("foragers/spawn-control-policy", {
          auto_spawn_auto_approve_enabled: enabled,
        });
        onPolicyChange(updated);
        toast.success(
          enabled
            ? "Auto approve enabled — eligible harvest spawns run without manual confirm."
            : "Manual mode — forager spawns wait for your approval.",
        );
      } catch (exc) {
        const msg = exc instanceof HiveApiError ? exc.message : "Policy update failed.";
        toast.error(msg);
      } finally {
        setAutoApproveBusy(false);
      }
    },
    [onPolicyChange],
  );

  const pauseAllVisible = useCallback(async () => {
    const activeRows = filteredRows.filter((row) => row.is_active);
    if (activeRows.length === 0) {
      return;
    }
    const confirmed = window.confirm(`Pause ${activeRows.length} forager${activeRows.length === 1 ? "" : "s"} shown here?`);
    if (!confirmed) {
      return;
    }
    setPauseAllBusy(true);
    try {
      await Promise.all(
        activeRows.map((row) => hivePostJson(`foragers/${encodeURIComponent(row.id)}/toggle`, { enabled: false })),
      );
      toast.success(`Paused ${activeRows.length} forager${activeRows.length === 1 ? "" : "s"}.`);
      await onReload();
    } catch (exc) {
      const msg = exc instanceof HiveApiError ? exc.message : "Bulk pause failed.";
      toast.error(msg);
    } finally {
      setPauseAllBusy(false);
    }
  }, [filteredRows, onReload]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
        <input
          className="qs-input min-w-0 flex-1"
          placeholder="Filter foragers by source / type / schedule / status…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label
          className="flex shrink-0 items-center justify-between gap-2 rounded-lg border border-(--qs-border) bg-black/25 px-3 py-2 text-xs text-(--qs-text-2) md:min-w-[11.5rem]"
          title="Auto approve spawns agents from harvest rules without manual confirm."
        >
          <span className="whitespace-nowrap font-medium">
            {policy.auto_spawn_auto_approve_enabled ? "Auto approve" : "Manual"}
          </span>
          <HiveSwitch
            checked={Boolean(policy.auto_spawn_auto_approve_enabled)}
            disabled={!canManage || autoApproveBusy}
            aria-label="Toggle auto approve for forager spawns"
            onCheckedChange={(checked) => void patchAutoApprove(checked)}
          />
        </label>
        <QsSelect
          className="w-full min-w-0 md:w-40 md:shrink-0"
          value={statusFilter}
          onValueChange={(next) => setStatusFilter(next as StatusFilter)}
          options={[
            { value: "all", label: "all statuses" },
            { value: "ok", label: "active" },
            { value: "warn", label: "needs input" },
            { value: "paused", label: "paused" },
            { value: "error", label: "error" },
          ]}
        />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">
            Configurations
            {filteredRows.length > 0 ? (
              <span className="ml-2 font-normal normal-case tracking-normal text-(--qs-text-4)">
                ({filteredRows.length})
              </span>
            ) : null}
          </p>
        </div>

        <div className="v4-sessions-list-scroll hive-scrollbar">
          {filteredRows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-(--qs-border) bg-black/20 px-4 py-6 text-center">
              <p className="text-sm text-(--qs-text-2)">
                {configurations.length === 0
                  ? "No foragers yet — create one with New forager."
                  : "No foragers match this filter."}
              </p>
              {configurations.length > 0 ? (
                <button
                  type="button"
                  className="qs-btn qs-btn--ghost qs-btn--sm mt-3"
                  onClick={() => {
                    setQuery("");
                    setStatusFilter("all");
                  }}
                >
                  Reset filters
                </button>
              ) : null}
            </div>
          ) : (
            visibleRows.map((row) => {
              const forager = foragersById.get(row.id);
              const routeTags = [
                row.source_type,
                row.schedule_label,
                row.is_active ? "scheduled" : "paused",
                policy.auto_spawn_auto_approve_enabled ? "auto-spawn" : "manual-spawn",
              ];
              const skills = [
                ...(forager?.tools ?? []),
                ...(Array.isArray(forager?.filter_config?.skills)
                  ? (forager.filter_config.skills as string[])
                  : []),
              ].filter(Boolean);

              return (
                <div key={row.id} className="v4-session-row">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <span className="font-(family-name:--font-jetbrains-mono) text-[11px] text-(--qs-text-3)">
                        {shortForagerId(row.id)}
                      </span>
                      <V4Badge tone={statusTone(row.status)}>{statusLabel(row.status)}</V4Badge>
                      <V4Badge tone="purple">{row.source_type}</V4Badge>
                    </div>
                    <p className="v4-session-goal text-sm font-medium text-(--qs-text)" title={row.source_name}>
                      {row.source_name}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-(--qs-text-3)">
                      {forager?.description?.trim() || "Periodic harvest into HiveMind with optional auto-spawn rules."}
                    </p>

                    <div className="mt-2 space-y-1.5" data-testid="forager-config-pattern-skills">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-(--qs-text-3)">
                          Source routes
                        </p>
                        <V4Badge tone="info">heuristic-v1</V4Badge>
                        {row.status === "warn" ? <V4Badge tone="gold">review harvest</V4Badge> : null}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {routeTags.map((tag) => (
                          <V4Badge key={`${row.id}-${tag}`} tone="info">
                            {tag}
                          </V4Badge>
                        ))}
                      </div>
                      {skills.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-[10px] font-medium uppercase tracking-wider text-(--qs-text-4)">
                            Required skills
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {skills.slice(0, 8).map((slug) => (
                              <ForagerSkillBadge key={`${row.id}-${slug}`} slug={slug} />
                            ))}
                          </div>
                        </div>
                      ) : null}
                      <ForagerProgressCell
                        pct={row.run_progress_pct ?? 0}
                        detail={row.progress_detail}
                        href={
                          resultsReportReady(row)
                            ? null
                            : row.progress_href ??
                              foragerKnowledgeHref({ foragerId: row.id, searchQuery: row.source_name })
                        }
                        onActivate={
                          resultsReportReady(row)
                            ? () => openResults(row)
                            : undefined
                        }
                      />
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <span className="text-xs text-(--qs-text-3)">
                      {formatTimeAgoSeconds(row.last_run_seconds_ago)} · {row.items_count} items
                    </span>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      onClick={() => openResults(row)}
                    >
                      <FileText className="h-3.5 w-3.5" aria-hidden />
                      Results
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      disabled={!canManage || busy === `task-${row.id}`}
                      onClick={() => void onPromoteTask(row)}
                    >
                      <ListTodo className="h-3.5 w-3.5" aria-hidden />
                      Task
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      disabled={!canManage || busy === `run-${row.id}` || isForagerSessionLive(row)}
                      title={
                        isForagerSessionLive(row)
                          ? "Supervisor session is already running — wait for it to finish."
                          : undefined
                      }
                      onClick={() => void onRun(row.id)}
                    >
                      <Play className="h-3.5 w-3.5" aria-hidden />
                      Run
                    </button>
                    {row.is_active ? (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={!canManage || busy === `toggle-${row.id}`}
                        onClick={() => void onToggleActive(row, false)}
                      >
                        Pause
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="qs-btn qs-btn--ghost qs-btn--sm"
                        disabled={!canManage || busy === `toggle-${row.id}`}
                        onClick={() => void onToggleActive(row, true)}
                      >
                        Resume
                      </button>
                    )}
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                      disabled={!canManage}
                      onClick={() => onEdit(row.id)}
                    >
                      <Pencil className="h-3.5 w-3.5" aria-hidden />
                      Edit
                    </button>
                    <button
                      type="button"
                      className={cn(
                        "qs-btn qs-btn--danger qs-btn--sm gap-1.5",
                        busy === `delete-${row.id}` && "opacity-60",
                      )}
                      disabled={!canManage || busy === `delete-${row.id}`}
                      onClick={() => onDelete(row)}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      Delete
                    </button>
                    {row.status === "warn" ? (
                      <>
                        <button
                          type="button"
                          className="qs-btn qs-btn--green qs-btn--sm"
                          disabled={
                            !canManage || busy === `run-${row.id}` || isForagerSessionLive(row)
                          }
                          title={
                            isForagerSessionLive(row)
                              ? "Supervisor session is already running — wait for it to finish."
                              : undefined
                          }
                          onClick={() => void onRun(row.id)}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          className="qs-btn qs-btn--danger qs-btn--sm"
                          disabled={!canManage || busy === `toggle-${row.id}`}
                          onClick={() => void onToggleActive(row, false)}
                        >
                          Reject
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {hiddenConfigurationCount > 0 && !showAllConfigurations ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            disabled={pauseAllBusy || busy !== null}
            onClick={() => setShowAllConfigurations(true)}
          >
            Show all ({filteredRows.length})
          </button>
        ) : null}
        {showAllConfigurations && filteredRows.length > FORAGER_CONFIG_PREVIEW_LIMIT ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost mt-3 w-full justify-center py-2.5 text-sm font-semibold"
            onClick={() => setShowAllConfigurations(false)}
          >
            Show less
          </button>
        ) : null}

        {filteredRows.some((row) => row.is_active) ? (
          <button
            type="button"
            className="qs-btn qs-btn--danger mt-3 w-full justify-center py-2.5 text-sm font-semibold disabled:opacity-45"
            disabled={!canManage || pauseAllBusy || busy !== null}
            onClick={() => void pauseAllVisible()}
          >
            {pauseAllBusy
              ? "Pausing…"
              : query.trim() || statusFilter !== "all"
                ? `Pause filtered (${filteredRows.filter((row) => row.is_active).length})`
                : `Pause all (${filteredRows.filter((row) => row.is_active).length})`}
          </button>
        ) : null}
      </div>

      <ForagerResultsDialog
        foragerId={resultsForager?.id ?? null}
        sourceName={resultsForager?.name}
        open={resultsForager !== null}
        onOpenChange={(next) => {
          if (!next) {
            setResultsForager(null);
          }
        }}
      />
    </div>
  );
}

export const ForagerConfigurationsPanel = memo(ForagerConfigurationsPanelInner);
