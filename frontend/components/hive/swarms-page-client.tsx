"use client";

import {
  ArrowRight,
  Pencil,
  Plus,
  Radio,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { HivePageShell } from "@/components/hive/hive-page-shell";
import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { SwarmsColoniesGrid } from "@/components/hive/swarms-colonies-grid";
import { SwarmsNewColonyDialog } from "@/components/hive/swarms-new-colony-dialog";
import { SubSwarmLocalMindPanel } from "@/components/hive/sub-swarm-local-mind-panel";
import { SwarmHealthNotesPanel } from "@/components/hive/swarm-health-notes-panel";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
  V4IconAgents,
  V4IconPollen,
  V4IconSwarms,
  V4Stat,
} from "@/components/ui/v4";
import { HiveApiError, hiveGet, hivePatchJson, hivePostJson } from "@/lib/api";
import { hivePageShellError } from "@/lib/hive-page-error";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import type { SwarmsOverviewColony, SwarmsOverviewPayload, WaggleFeedItem } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

function formatPollen(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return String(Math.round(n * 10) / 10);
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatAgo(sec: number | null): string {
  if (sec == null) return "awaiting";
  if (sec < 60) return `${sec}s ago`;
  const m = Math.floor(sec / 60);
  if (m < 90) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function formatWaggleClock(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function laneFromFeed(item: WaggleFeedItem): { from: string; to: string } {
  const cap = (lane: string) => lane.charAt(0).toUpperCase() + lane.slice(1);
  return {
    from: cap(item.source_lane || item.source_label.split("-")[0] || item.source_label),
    to: cap(item.target_lane || item.target_label.split("-")[0] || item.target_label),
  };
}

export function SwarmsPageClient() {
  const [data, setData] = useState<SwarmsOverviewPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [openColonyId, setOpenColonyId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const payload = await hiveGet<SwarmsOverviewPayload>("dashboard/swarms-overview");
      setData(payload);
      setErr(null);
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Swarms overview unreachable";
      setErr(msg);
    }
  }, []);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  async function withBusy<T>(key: string, fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(key);
    try {
      return await fn();
    } finally {
      setBusy(null);
    }
  }

  async function hiveSyncAckAll(): Promise<void> {
    if (!data?.colonies.length) return;
    await withBusy("sync-ack", async () => {
      await Promise.all(
        data.colonies.filter((c) => c.is_active).map((c) => hivePostJson(`swarms/${c.id}/global-sync`, {})),
      );
      toast.success("Hive sync acknowledged for all active colonies");
      await reload();
    });
  }

  async function wakeAllBees(): Promise<void> {
    if (!data?.colonies.length) return;
    await withBusy("wake-all", async () => {
      const results = await Promise.all(
        data.colonies.map((c) => hivePostJson<{ nudged_agents?: number }>(`swarms/${c.id}/wake`, {})),
      );
      const nudged = results.reduce((sum, r) => sum + (r.nudged_agents ?? 0), 0);
      toast.success(`Woke ${nudged} bee${nudged === 1 ? "" : "s"} across colonies`);
      await reload();
    });
  }

  async function forceHiveSync(): Promise<void> {
    await hiveSyncAckAll();
  }

  async function toggleColonyPause(colony: SwarmsOverviewColony): Promise<void> {
    await withBusy(`pause-${colony.id}`, async () => {
      await hivePatchJson(`swarms/${colony.id}`, { is_active: !colony.is_active });
      toast.success(colony.is_active ? `${colony.display_name} paused` : `${colony.display_name} resumed`);
      await reload();
    });
  }

  async function wakeColony(colony: SwarmsOverviewColony): Promise<void> {
    await withBusy(`wake-${colony.id}`, async () => {
      const res = await hivePostJson<{ nudged_agents?: number }>(`swarms/${colony.id}/wake`, {});
      toast.success(`Nudged ${res.nudged_agents ?? 0} agents in ${colony.display_name}`);
      await reload();
    });
  }

  const kpis = data?.kpis;
  const syncMin = Math.max(1, Math.round((data?.hive_sync_interval_sec ?? 300) / 60));
  const liveCount = kpis?.colonies_active ?? 0;

  if (!data) {
    return (
      <HivePageShell
        title="Swarms"
        subtitle="Colony control plane"
        hintKey="swarms"
        error={hivePageShellError(err, () => setErr(null))}
      >
        <HivePanelSectionSkeleton label="Loading swarms overview" minHeightClass="min-h-[20rem]" />
      </HivePageShell>
    );
  }

  return (
    <HivePageShell
      title="Swarms"
      subtitle={`Colony control plane — decentralized sub-hives with local memory, global sync every ${syncMin} min.`}
      hintKey="swarms"
      error={hivePageShellError(err, () => setErr(null))}
      status={
        <span className="v4-status-pill inline-flex">
          <span className="hive-pulse-dot" aria-hidden />
          {liveCount} {liveCount === 1 ? "Colony" : "Colonies"} live
        </span>
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
            disabled={busy === "sync-ack"}
            onClick={() => void hiveSyncAckAll()}
          >
            <RefreshCw className={cn("h-4 w-4 shrink-0", busy === "sync-ack" && "animate-spin")} aria-hidden />
            Hive sync ACK
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
            disabled={busy === "wake-all"}
            onClick={() => void wakeAllBees()}
          >
            <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
            Wake all bees
          </button>
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-4 w-4 shrink-0" aria-hidden />
            New colony
          </button>
          <Link href="/swarms/new" className="qs-btn qs-btn--ghost qs-btn--sm gap-2">
            <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
            Open Swarm Builder
          </Link>
        </div>
      }
    >
      <V4Card tight className="border-(--qs-cyan)/30 bg-(--qs-cyan)/[0.04]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-(--qs-text)">
              👑 Queen policy — orchestrator + curated memory
            </p>
            <p className="mt-1 text-xs text-(--qs-text-3)">
              Hive-wide mission, behavioral instructions, and priorities. Per-swarm
              manager prompts editable from each colony row below.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={
                data?.orchestrator_agent_id
                  ? `/agents/${encodeURIComponent(data.orchestrator_agent_id)}/edit`
                  : "#"
              }
              aria-disabled={!data?.orchestrator_agent_id}
              className={cn(
                "qs-btn qs-btn--cyan qs-btn--sm gap-1.5",
                !data?.orchestrator_agent_id && "pointer-events-none opacity-40",
              )}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden />
              Edit Orchestrator prompt
            </Link>
            <Link
              href="/settings/harness#curated-memory"
              className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden />
              Curated memory (Mission / Instructions)
            </Link>
          </div>
        </div>
      </V4Card>

      <div className="v4-stat-grid">
        {!data ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="v4-stat h-[120px] animate-pulse bg-white/5" />
          ))
        ) : (
          <>
            <V4Stat
              label="Colonies"
              value={kpis?.colonies_total ?? 0}
              icon={V4IconSwarms}
              iconTone="purple"
              foot={`${kpis?.colonies_active ?? 0} active · ${kpis?.colonies_paused ?? 0} paused`}
            />
            <V4Stat
              label="Total bees"
              value={kpis?.total_bees ?? 0}
              icon={V4IconAgents}
              foot={`${kpis?.bees_working ?? 0} working · ${kpis?.bees_idle ?? 0} idle`}
            />
            <V4Stat
              label="Pollen pool"
              value={formatPollen(kpis?.pollen_pool ?? 0)}
              icon={V4IconPollen}
              iconTone="green"
            />
            <V4Stat
              label="Avg sync drift"
              value={formatDuration(kpis?.avg_sync_drift_sec ?? 0)}
              icon={Radio}
              iconTone="cyan"
              valueVariant="text"
              foot={
                kpis?.last_global_tick_sec != null
                  ? `Last global tick ${formatDuration(kpis.last_global_tick_sec)} ago`
                  : "Awaiting first global tick"
              }
            />
          </>
        )}
      </div>

      <V4Card tight>
        <V4CardHeader
          title="Colonies"
          description="Each colony is a decentralized SubSwarm running LangGraph locally; Maynard-Cross pollen rewards apply."
          hint={sectionHintNode("swarmsColonies")}
          actions={
            data?.colonies.length ? (
              <span className="v4-field-label tabular-nums">All colonies ({data.colonies.length})</span>
            ) : null
          }
        />

        {!data ? (
          <div className="grid gap-3 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="v4-dream-cycle-card h-[220px] animate-pulse bg-white/5" />
            ))}
          </div>
        ) : (
          <SwarmsColoniesGrid
            colonies={data.colonies}
            syncMin={syncMin}
            busy={busy}
            openColonyId={openColonyId}
            onTogglePause={(colony) => void toggleColonyPause(colony)}
            onOpenColony={(colony) => {
              setOpenColonyId((cur) => (cur === colony.id ? null : colony.id));
              if (colony.status === "paused") {
                void wakeColony(colony);
              }
            }}
          />
        )}

        {openColonyId ? (
          <div className="mt-4 rounded-(--qs-radius-sm) border border-(--qs-border) bg-white/[0.02] p-4">
            {(() => {
              const colony = data?.colonies.find((c) => c.id === openColonyId);
              if (!colony) return null;
              return (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-(--qs-text)">{colony.display_name}</p>
                      <p className="mt-1 text-xs text-(--qs-text-3)">
                        {colony.member_count} bees · {colony.lane_label} lane · queen {colony.queen_label}
                      </p>
                    </div>
                  <div className="v4-dream-cycle-card-actions">
                    <Link href={`/agents/new?swarm_id=${encodeURIComponent(colony.id)}`} className="qs-btn qs-btn--ghost qs-btn--sm">
                      Assign bee
                    </Link>
                    <Link href="/agents" className="qs-btn qs-btn--ghost qs-btn--sm">
                      Open roster
                    </Link>
                  </div>
                  </div>
                  <SwarmHealthNotesPanel swarmId={colony.id} onChanged={() => void reload()} />
                  <SubSwarmLocalMindPanel swarmId={colony.id} onSynced={() => void reload()} />
                </div>
              );
            })()}
          </div>
        ) : null}
      </V4Card>

      <div className="v4-cols-2 v4-cols-2--stack-mobile">
        <V4Card className="h-full">
          <V4CardHeader
            title="Waggle dance feed"
            description="Realtime cross-swarm signals — backed by hive tasks topic."
            hint={sectionHintNode("swarmsWaggleFeed")}
            as="h3"
            actions={<V4Badge tone="purple">live</V4Badge>}
          />
          {!data?.waggle_feed.length ? (
            <p className="text-sm text-(--qs-text-3)">No cross-swarm handoffs yet — run a workflow or enqueue tasks.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {data.waggle_feed.map((item, i) => {
                const lanes = laneFromFeed(item);
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "flex gap-3",
                      i < data.waggle_feed.length - 1 && "border-b border-(--qs-border) pb-3",
                    )}
                  >
                    <span className="v4-waggle-time">{formatWaggleClock(item.occurred_at)}</span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                        <span className="text-pollen">{lanes.from}</span>
                        <ArrowRight className="h-2.5 w-2.5 text-(--qs-text-3)" aria-hidden />
                        <span className="text-(--qs-purple-bright)">{lanes.to}</span>
                      </div>
                      <p className="text-sm text-(--qs-text-2)">{item.message}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </V4Card>

        <V4Card className="h-full">
          <V4CardHeader
            title="Hive sync"
            description={`Global state convergence — Celery beat tick every ${syncMin} min.`}
            as="h3"
            actions={
              <button
                type="button"
                className="qs-btn qs-btn--ghost qs-btn--sm gap-2"
                disabled={busy === "sync-ack"}
                onClick={() => void forceHiveSync()}
              >
                <RefreshCw className={cn("h-4 w-4", busy === "sync-ack" && "animate-spin")} aria-hidden />
                Force sync
              </button>
            }
          />
          <div className="flex flex-col gap-4">
            {(data?.hive_sync ?? []).map((row) => (
              <div key={row.label} className="v4-hive-sync-row">
                <div className="flex items-center gap-3">
                  <V4Badge tone={row.state === "synced" ? "ok" : "info"}>{row.state}</V4Badge>
                  <span className="text-sm text-(--qs-text)">{row.label}</span>
                </div>
                <span className="text-xs text-(--qs-text-3)">
                  {row.state === "syncing" && row.seconds_ago == null
                    ? "in progress"
                    : formatAgo(row.seconds_ago)}
                </span>
              </div>
            ))}
          </div>
        </V4Card>
      </div>

      <SwarmsNewColonyDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          setCreateOpen(false);
          void reload();
        }}
      />
    </HivePageShell>
  );
}
