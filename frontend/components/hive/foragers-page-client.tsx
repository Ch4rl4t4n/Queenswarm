"use client";

import { Pencil, Play, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ForagerFormDialog } from "@/components/hive/forager-form-dialog";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { ResponsiveTable } from "@/components/ui/responsive-table";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4Chip,
  V4IconAgents,
  V4IconForagers,
  V4IconKnowledge,
  V4IconPollen,
  V4PageCanvas,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import type {
  ForagerRow,
  ForagersOverviewConfiguration,
  ForagersOverviewPayload,
  ForagersSpawnRule,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";

type FilterKey = "all" | "active" | "paused" | "errors";

interface AgentTemplateLite {
  id: string;
  name: string;
  category: string;
}

interface TeamOverviewResponse {
  tenant_role: string;
}

function formatCount(n: number): string {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return String(n);
}

function formatChunks(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

function formatAgo(sec: number | null): string {
  if (sec == null) return "never";
  if (sec < 60) return `${sec}s ago`;
  const m = Math.floor(sec / 60);
  if (m < 90) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function statusTone(status: ForagersOverviewConfiguration["status"]): "ok" | "warn" | "err" | "purple" {
  if (status === "ok") return "ok";
  if (status === "warn") return "warn";
  if (status === "error") return "err";
  return "purple";
}

function matchesFilter(row: ForagersOverviewConfiguration, filter: FilterKey): boolean {
  if (filter === "all") return true;
  if (filter === "active") return row.is_active && row.status !== "error";
  if (filter === "paused") return !row.is_active || row.status === "paused";
  if (filter === "errors") return row.status === "error";
  return true;
}

function SpawnRuleToggle({
  enabled,
  disabled,
  onToggle,
}: {
  enabled: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      className={cn("v4-toggle", enabled && "v4-toggle--on")}
      onClick={onToggle}
    >
      <span className="v4-toggle-knob" aria-hidden />
    </button>
  );
}

export function ForagersPageClient() {
  const [data, setData] = useState<ForagersOverviewPayload | null>(null);
  const [foragers, setForagers] = useState<ForagerRow[]>([]);
  const [templates, setTemplates] = useState<AgentTemplateLite[]>([]);
  const [tenantRole, setTenantRole] = useState("guest");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editingForager, setEditingForager] = useState<ForagerRow | null>(null);

  const canManage = tenantRole === "owner" || tenantRole === "admin";

  const reload = useCallback(async () => {
    try {
      const [overview, rows, team, templateRows] = await Promise.all([
        hiveGet<ForagersOverviewPayload>("dashboard/foragers-overview"),
        hiveGet<ForagerRow[]>("foragers"),
        hiveGet<TeamOverviewResponse>("settings/team"),
        hiveGet<AgentTemplateLite[]>("agent-templates"),
      ]);
      setData(overview);
      setForagers(rows);
      setTenantRole(String(team.tenant_role || "guest"));
      setTemplates(templateRows);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Foragers overview unreachable";
      setErr(msg);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const [overview, rows, team, templateRows] = await Promise.all([
          hiveGet<ForagersOverviewPayload>("dashboard/foragers-overview"),
          hiveGet<ForagerRow[]>("foragers"),
          hiveGet<TeamOverviewResponse>("settings/team"),
          hiveGet<AgentTemplateLite[]>("agent-templates"),
        ]);
        if (!alive) return;
        setData(overview);
        setForagers(rows);
        setTenantRole(String(team.tenant_role || "guest"));
        setTemplates(templateRows);
        setErr(null);
      } catch (e) {
        if (!alive) return;
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Foragers overview unreachable";
        setErr(msg);
      }
    })();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void reload();
      }
    }, COCKPIT_POLL_BOARD_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [reload]);

  const kpis = data?.kpis;
  const configurations = data?.configurations ?? [];
  const spawnRules = data?.spawn_rules ?? [];

  const filterCounts = useMemo(
    () => ({
      all: configurations.length,
      active: configurations.filter((row) => matchesFilter(row, "active")).length,
      paused: configurations.filter((row) => matchesFilter(row, "paused")).length,
      errors: configurations.filter((row) => matchesFilter(row, "errors")).length,
    }),
    [configurations],
  );

  const visibleRows = useMemo(
    () => configurations.filter((row) => matchesFilter(row, filter)),
    [configurations, filter],
  );

  async function withBusy<T>(key: string, fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(key);
    try {
      return await fn();
    } finally {
      setBusy(null);
    }
  }

  function openCreate() {
    setEditingForager(null);
    setFormOpen(true);
  }

  function openEdit(id: string) {
    const row = foragers.find((item) => item.id === id) ?? null;
    setEditingForager(row);
    setFormOpen(true);
  }

  async function triggerRun(id: string) {
    if (!canManage) return;
    await withBusy(`run-${id}`, async () => {
      await hivePostJson(`foragers/${encodeURIComponent(id)}/trigger`, { records: [] });
      toast.success("Forager run triggered");
      await reload();
    });
  }

  async function runAllNow() {
    if (!canManage || !configurations.length) return;
    await withBusy("run-all", async () => {
      const active = configurations.filter((row) => row.is_active);
      await Promise.all(
        active.map((row) => hivePostJson(`foragers/${encodeURIComponent(row.id)}/trigger`, { records: [] })),
      );
      toast.success(`Triggered ${active.length} forager${active.length === 1 ? "" : "s"}`);
      await reload();
    });
  }

  async function toggleSpawnRule(rule: ForagersSpawnRule) {
    if (!canManage) return;
    const forager = foragers.find((row) => row.id === rule.forager_id);
    if (!forager) return;

    await withBusy(`rule-${rule.id}`, async () => {
      const filterCfg = { ...(forager.filter_config || {}) };
      const rules = Array.isArray(filterCfg.auto_spawn_rules) ? [...filterCfg.auto_spawn_rules] : [];
      const nextEnabled = !rule.enabled;

      if (rules.length > 0) {
        filterCfg.auto_spawn_rules = rules.map((entry: unknown) => {
          if (typeof entry !== "object" || entry === null) return entry;
          const row = entry as Record<string, unknown>;
          const rowId = String(row.id ?? "");
          if (rowId === rule.id || rowId === rule.id.split(":")[0]) {
            return { ...row, enabled: nextEnabled };
          }
          return entry;
        });
      } else {
        filterCfg.auto_spawn_rules = [
          {
            id: rule.id,
            when_label: rule.when_label,
            spawn_label: rule.spawn_label,
            cooldown: rule.cooldown,
            enabled: nextEnabled,
          },
        ];
      }

      await hivePutJson(`foragers/${encodeURIComponent(forager.id)}`, {
        filter_config: filterCfg,
      });
      toast.success(nextEnabled ? "Auto-spawn rule enabled" : "Auto-spawn rule paused");
      await reload();
    });
  }

  if (err && !data) {
    return (
      <V4PageCanvas>
        <HivePageHeader
          title="Foragers"
          subtitle="Data-collectors that feed HiveMind — schedule them, watch them ingest, then auto-spawn agents from harvested context."
        />
        <V4Card>
          <p className="text-sm text-(--qs-red)">{err}</p>
        </V4Card>
      </V4PageCanvas>
    );
  }

  const trendPct = kpis?.items_trend_pct;

  return (
    <V4PageCanvas>
      <HivePageHeader
        title="Foragers"
        subtitle="Data-collectors that feed HiveMind — schedule them, watch them ingest, then auto-spawn agents from harvested context."
        actions={
          <>
            <button
              type="button"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
              disabled={!canManage || busy === "run-all" || !configurations.length}
              onClick={() => void runAllNow()}
            >
              <RefreshCw className={cn("h-4 w-4", busy === "run-all" && "animate-spin")} aria-hidden />
              Run all now
            </button>
            <button
              type="button"
              className="qs-btn qs-btn--primary qs-btn--sm gap-2"
              disabled={!canManage}
              onClick={openCreate}
            >
              <Plus className="h-4 w-4" aria-hidden />
              New forager
            </button>
          </>
        }
      />

      <div className="v4-stat-grid">
        {!data ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="v4-stat h-[120px] animate-pulse bg-white/5" />
          ))
        ) : (
          <>
            <V4Stat
              label="Active foragers"
              value={kpis?.foragers_total ?? 0}
              icon={V4IconForagers}
              iconTone="purple"
              foot={`${kpis?.foragers_paused ?? 0} paused · ${kpis?.foragers_error ?? 0} error${(kpis?.foragers_error ?? 0) === 1 ? "" : "s"}`}
            />
            <V4Stat
              label="Items ingested · 24h"
              value={formatCount(kpis?.items_ingested_24h ?? 0)}
              icon={V4IconPollen}
              trend={
                trendPct != null
                  ? { dir: trendPct >= 0 ? "up" : "down", text: `${trendPct >= 0 ? "+" : ""}${trendPct}% vs avg` }
                  : undefined
              }
              foot={trendPct == null ? "Building baseline" : undefined}
            />
            <V4Stat
              label="HiveMind chunks"
              value={formatChunks(kpis?.hivemind_chunks_7d ?? 0)}
              icon={V4IconKnowledge}
              iconTone="cyan"
              foot="embedded last 7d"
            />
            <V4Stat
              label="Auto-spawned bees"
              value={kpis?.auto_spawned_bees ?? 0}
              icon={V4IconAgents}
              iconTone="green"
              foot="routed to swarms"
            />
          </>
        )}
      </div>

      <V4Card>
        <V4CardHeader
          title="Forager configurations"
          description="YouTube / RSS / API · periodicity · HiveMind ingest · auto-spawn rules."
          actions={
            <div className="v4-chip-scroll v4-foragers-filter-chips">
              <V4Chip active={filter === "all"} count={filterCounts.all} onClick={() => setFilter("all")}>
                All
              </V4Chip>
              <V4Chip active={filter === "active"} count={filterCounts.active} onClick={() => setFilter("active")}>
                Active
              </V4Chip>
              <V4Chip active={filter === "paused"} count={filterCounts.paused} onClick={() => setFilter("paused")}>
                Paused
              </V4Chip>
              <V4Chip active={filter === "errors"} count={filterCounts.errors} onClick={() => setFilter("errors")}>
                Errors
              </V4Chip>
            </div>
          }
        />
        <ResponsiveTable
          table={
            <table className="v4-data-table min-w-[920px]">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Schedule</th>
                  <th>Last run</th>
                  <th>Items</th>
                  <th>Status</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {!visibleRows.length ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-sm text-(--qs-text-3)">
                      {configurations.length
                        ? "No foragers match this filter."
                        : "No foragers yet — create one with New forager."}
                    </td>
                  </tr>
                ) : (
                  visibleRows.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <div className="v4-task-name">{row.source_name}</div>
                      </td>
                      <td>
                        <V4Badge tone="purple">{row.source_type}</V4Badge>
                      </td>
                      <td className="font-mono text-xs text-(--qs-text-2)">{row.schedule_label}</td>
                      <td className="text-(--qs-text-3)">{formatAgo(row.last_run_seconds_ago)}</td>
                      <td>{row.items_count}</td>
                      <td>
                        <V4Badge tone={statusTone(row.status)}>{row.status}</V4Badge>
                      </td>
                      <td>
                        <div className="flex flex-wrap justify-end gap-2">
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                            disabled={!canManage || busy === `run-${row.id}`}
                            onClick={() => void triggerRun(row.id)}
                          >
                            <Play className="h-3.5 w-3.5" aria-hidden />
                            Run
                          </button>
                          <button
                            type="button"
                            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
                            disabled={!canManage}
                            onClick={() => openEdit(row.id)}
                          >
                            <Pencil className="h-3.5 w-3.5" aria-hidden />
                            Edit
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          }
          cards={
            !visibleRows.length ? (
              <p className="py-8 text-center text-sm text-(--qs-text-3)">
                {configurations.length ? "No foragers match this filter." : "No foragers yet — create one with New forager."}
              </p>
            ) : (
              visibleRows.map((row) => (
                <article key={row.id} className="v4-mobile-card-row">
                  <div className="v4-mobile-card-row__head">
                    <div className="min-w-0">
                      <div className="v4-task-name">{row.source_name}</div>
                      <div className="text-xs text-(--qs-text-3)">{row.schedule_label}</div>
                    </div>
                    <V4Badge tone={statusTone(row.status)}>{row.status}</V4Badge>
                  </div>
                  <div className="v4-mobile-card-row__meta">
                    <V4Badge tone="purple">{row.source_type}</V4Badge>
                    <span>{formatAgo(row.last_run_seconds_ago)}</span>
                    <span>{row.items_count} items</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm flex-1 gap-1.5"
                      disabled={!canManage || busy === `run-${row.id}`}
                      onClick={() => void triggerRun(row.id)}
                    >
                      <Play className="h-3.5 w-3.5" aria-hidden />
                      Run
                    </button>
                    <button
                      type="button"
                      className="qs-btn qs-btn--ghost qs-btn--sm flex-1 gap-1.5"
                      disabled={!canManage}
                      onClick={() => openEdit(row.id)}
                    >
                      <Pencil className="h-3.5 w-3.5" aria-hidden />
                      Edit
                    </button>
                  </div>
                </article>
              ))
            )
          }
        />
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Auto-spawn rules"
          description="When a forager finds X items matching a query, spawn a ScoutBee in target swarm."
          actions={
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" disabled={!canManage} onClick={openCreate}>
              <Plus className="h-4 w-4" aria-hidden />
              Add rule
            </button>
          }
        />
        <div className="flex flex-col gap-3">
          {!spawnRules.length ? (
            <p className="text-sm text-(--qs-text-3)">
              No auto-spawn rules yet. Link an agent template to a forager or add rules in filter config.
            </p>
          ) : (
            spawnRules.map((rule) => (
              <div key={rule.id} className="v4-spawn-rule">
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
                  <V4Badge tone="info">when</V4Badge>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-(--qs-text-1)">{rule.when_label}</div>
                    <div className="mt-0.5 text-xs text-(--qs-text-3)">
                      → spawn <span className="text-pollen">{rule.spawn_label}</span> · cooldown {rule.cooldown}
                    </div>
                  </div>
                </div>
                <SpawnRuleToggle
                  enabled={rule.enabled}
                  disabled={!canManage || busy === `rule-${rule.id}`}
                  onToggle={() => void toggleSpawnRule(rule)}
                />
              </div>
            ))
          )}
        </div>
      </V4Card>

      <ForagerFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        editingForager={editingForager}
        templates={templates}
        canManage={canManage}
        onSaved={() => void reload()}
      />
    </V4PageCanvas>
  );
}
