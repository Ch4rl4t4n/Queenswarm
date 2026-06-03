"use client";

import { Plus, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { ForagerConfigurationsPanel } from "@/components/hive/forager-configurations-panel";
import { ForagerFormDialog } from "@/components/hive/forager-form-dialog";
import { ForagerSpawnRuleDialog } from "@/components/hive/forager-spawn-rule-dialog";
import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4IconAgents,
  V4IconForagers,
  V4IconKnowledge,
  V4IconPollen,
  V4Stat,
} from "@/components/ui/v4";
import {
  AGENTS_HUB_PATH,
  EXECUTION_LANE_CROSS_LINK_LABELS,
  KNOWLEDGE_HIVEMIND_HREF,
} from "@/lib/execution-lane-routes";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type {
  ForagerRow,
  ForagersOverviewConfiguration,
  ForagersOverviewPayload,
  ForagersSpawnPolicy,
  ForagersSpawnRule,
} from "@/lib/hive-types";
import { cn } from "@/lib/utils";
import { HiveApiError, hiveDelete, hiveGet, hivePostJson, hivePutJson } from "@/lib/api";
import { hivePageShellError } from "@/lib/hive-page-error";

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
  const [formOpen, setFormOpen] = useState(false);
  const [spawnRuleOpen, setSpawnRuleOpen] = useState(false);
  const [editingForager, setEditingForager] = useState<ForagerRow | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ForagersOverviewConfiguration | null>(null);
  const [spawnPolicy, setSpawnPolicy] = useState<ForagersSpawnPolicy>({
    auto_spawn_auto_approve_enabled: false,
  });

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
      setSpawnPolicy(
        overview.policy ?? {
          auto_spawn_auto_approve_enabled: false,
        },
      );
      setForagers(rows);
      setTenantRole(String(team.tenant_role || "guest"));
      setTemplates(templateRows);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Foragers overview unreachable";
      setErr(msg);
    }
  }, []);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  const kpis = data?.kpis;
  const configurations = useMemo(() => data?.configurations ?? [], [data?.configurations]);
  const spawnRules = data?.spawn_rules ?? [];
  const foragersById = useMemo(() => new Map(foragers.map((row) => [row.id, row])), [foragers]);

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
      const res = await hivePostJson<{
        status: string;
        routine_session_id?: string | null;
      }>(`foragers/${encodeURIComponent(id)}/trigger`, { records: [] });
      if (res.status === "already_running") {
        toast.info("Forager session already running — wait for it to finish.");
      } else {
        toast.success("Forager run triggered");
      }
      await reload();
    });
  }

  async function runAllNow() {
    if (!canManage || !configurations.length) return;
    await withBusy("run-all", async () => {
      const active = configurations.filter((row) => row.is_active && row.progress_kind !== "live_run");
      if (!active.length) {
        toast.info("All active foragers are already running.");
        return;
      }
      const skipped = configurations.filter((row) => row.is_active && row.progress_kind === "live_run").length;
      await Promise.all(
        active.map((row) => hivePostJson(`foragers/${encodeURIComponent(row.id)}/trigger`, { records: [] })),
      );
      toast.success(
        skipped > 0
          ? `Triggered ${active.length} forager${active.length === 1 ? "" : "s"} (${skipped} already running)`
          : `Triggered ${active.length} forager${active.length === 1 ? "" : "s"}`,
      );
      await reload();
    });
  }

  async function promoteToTask(row: ForagersOverviewConfiguration) {
    if (!canManage) return;
    await withBusy(`task-${row.id}`, async () => {
      const res = await hivePostJson<{ ok: boolean; task_id?: string; title?: string }>(
        `foragers/${encodeURIComponent(row.id)}/promote-task`,
        { title: `Forager digest · ${row.source_name}` },
      );
      toast.success(res.title ? `${res.title} → Triage` : "Digest task created in Mission Kanban");
      await reload();
    });
  }

  async function confirmDeleteForager() {
    if (!canManage || !deleteTarget) return;
    const target = deleteTarget;
    setDeleteTarget(null);
    await withBusy(`delete-${target.id}`, async () => {
      await hiveDelete<void>(`foragers/${encodeURIComponent(target.id)}`);
      toast.success(`Deleted ${target.source_name}`);
      await reload();
    });
  }

  async function toggleForagerActive(row: ForagersOverviewConfiguration, enabled: boolean) {
    if (!canManage) return;
    await withBusy(`toggle-${row.id}`, async () => {
      await hivePostJson(`foragers/${encodeURIComponent(row.id)}/toggle`, { enabled });
      toast.success(enabled ? `${row.source_name} resumed` : `${row.source_name} paused`);
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

  if (!data) {
    return (
      <HivePageShell
        title="Foragers"
        subtitle="Data-collectors that feed HiveMind — schedule them, watch them ingest, then auto-spawn agents from harvested context."
        error={hivePageShellError(err, () => setErr(null))}
      >
        <HivePanelSectionSkeleton label="Loading foragers overview" minHeightClass="min-h-[20rem]" />
      </HivePageShell>
    );
  }

  const trendPct = kpis?.items_trend_pct;

  return (
    <HivePageShell
      title="Foragers"
      subtitle="Data-collectors that feed HiveMind — schedule them, watch them ingest, then auto-spawn agents from harvested context."
      error={hivePageShellError(err, () => setErr(null))}
      actions={
        <>
          <Link href={AGENTS_HUB_PATH} className="qs-btn qs-btn--ghost qs-btn--sm">
            {EXECUTION_LANE_CROSS_LINK_LABELS.toAgentsHub}
          </Link>
          <Link href={KNOWLEDGE_HIVEMIND_HREF} className="qs-btn qs-btn--ghost qs-btn--sm">
            {EXECUTION_LANE_CROSS_LINK_LABELS.toHiveMind}
          </Link>
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
    >
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
        />
        <ForagerConfigurationsPanel
          configurations={configurations}
          foragersById={foragersById}
          policy={spawnPolicy}
          canManage={canManage}
          busy={busy}
          onPolicyChange={setSpawnPolicy}
          onReload={reload}
          onRun={triggerRun}
          onPromoteTask={promoteToTask}
          onEdit={openEdit}
          onDelete={setDeleteTarget}
          onToggleActive={toggleForagerActive}
        />
      </V4Card>

      <V4Card>
        <V4CardHeader
          title="Auto-spawn rules"
          description="When a forager finds X items matching a query, spawn a ScoutBee in target swarm."
          actions={
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" disabled={!canManage} onClick={() => setSpawnRuleOpen(true)}>
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

      <ForagerSpawnRuleDialog
        open={spawnRuleOpen}
        onOpenChange={setSpawnRuleOpen}
        foragers={foragers}
        configurations={configurations}
        templates={templates}
        canManage={canManage}
        onSaved={() => void reload()}
      />

      <ForagerFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        editingForager={editingForager}
        templates={templates}
        canManage={canManage}
        onSaved={() => void reload()}
      />

      <ConfirmModal
        open={deleteTarget != null}
        title="Delete forager?"
        message={
          deleteTarget
            ? `Remove "${deleteTarget.source_name}" and stop its schedule. Items already in HiveMind are kept.`
            : ""
        }
        confirmLabel="Delete"
        danger
        onConfirm={() => void confirmDeleteForager()}
        onCancel={() => setDeleteTarget(null)}
      />
    </HivePageShell>
  );
}
