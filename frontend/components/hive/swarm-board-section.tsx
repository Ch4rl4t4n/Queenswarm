"use client";

import Link from "next/link";
import { ChevronRightIcon, RefreshCw, Search, Zap, Cpu, Activity } from "lucide-react";
import useSWR from "swr";

import { useCockpitTelemetry } from "@/components/hive/cockpit-telemetry-provider";
import {
  V4Badge,
  V4Card,
  V4CardHeader,
} from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { cockpitSwrKeys } from "@/lib/cockpit-swr-keys";
import { COCKPIT_POLL_SWARM_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import type { SwarmBoardCard, SwarmBoardResponse, WaggleFeedItem } from "@/lib/hive-types";
import { formatSyncDue, syncTone } from "@/lib/sub-swarm-local-mind-utils";
import { cn } from "@/lib/utils";

function useSwarmBoard() {
  const { wsConnected } = useCockpitTelemetry();
  const pollMs = wsConnected
    ? Math.max(COCKPIT_PERF.wsConnectedPollMs, COCKPIT_POLL_SWARM_BOARD_MS)
    : COCKPIT_POLL_SWARM_BOARD_MS;
  const pollOptions = useSwrVisiblePollOptions(pollMs);
  const { data, error, mutate } = useSWR<SwarmBoardResponse>(
    cockpitSwrKeys.swarmBoard(),
    () => hiveGet<SwarmBoardResponse>("dashboard/swarm-board"),
    { ...pollOptions, keepPreviousData: true, dedupingInterval: 20_000 },
  );
  const err = error instanceof Error ? error.message : error ? "Swarm board unreachable" : null;
  return { data: data ?? null, err, reload: () => void mutate() };
}

const LANE_ICON: Record<string, typeof Search> = {
  scout: Search,
  eval: Activity,
  sim: Cpu,
  action: Zap,
};

function formatAgo(sec: number | null): string {
  if (sec == null) return "no sync yet";
  if (sec < 45) return `${sec}s ago`;
  const m = Math.floor(sec / 60);
  if (m < 90) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function formatFeedAgo(sec: number): string {
  if (sec < 90) return `${sec}s ago`;
  return formatAgo(sec);
}

function SwarmCard({ card }: { card: SwarmBoardCard }) {
  const Icon = LANE_ICON[card.lane.toLowerCase()] ?? Zap;
  const mind = card.local_mind;
  return (
    <article className="v4-swarm-card">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="v4-stat-icon v4-stat-icon--purple">
            <Icon className="h-4 w-4" aria-hidden />
          </span>
          <span className="font-semibold text-(--qs-text)">{card.display_name}</span>
        </div>
        <V4Badge tone={card.is_active ? "ok" : "warn"}>{card.is_active ? "live" : "idle"}</V4Badge>
      </div>
      <p className="mt-2 text-xs text-(--qs-text-3)">{card.description || "Local memory · Chroma · 5min sync"}</p>
      {mind ? (
        <div className="mt-3 space-y-2">
          <div className="relative h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className={cn("h-full rounded-full", mind.needs_sync ? "bg-pollen" : "bg-success")}
              style={{ width: `${mind.sync_progress_pct}%` }}
            />
          </div>
          <p className="text-[10px] text-(--qs-text-3)">
            <V4Badge tone={syncTone(mind.needs_sync)}>{mind.needs_sync ? "sync due" : "local hive"}</V4Badge>
            {" · "}
            global in {formatSyncDue(mind.sync_due_in_sec)}
            {mind.wizard_template ? ` · ${mind.wizard_template}` : ""}
          </p>
        </div>
      ) : null}
      <div className="mt-3 flex gap-4 text-xs text-(--qs-text-3)">
        <span>
          <strong className="text-(--qs-text)">{card.member_count}</strong> bees
        </span>
        <span>
          <strong className="text-(--qs-text)">{card.avg_performance_pct}%</strong> perf
        </span>
        <span>
          <strong className="text-(--qs-text)">{formatAgo(card.last_sync_seconds_ago)}</strong>
        </span>
      </div>
      <Link href="/#hive-live-swarm" className="mt-3 inline-flex items-center gap-0.5 text-xs font-semibold text-(--qs-cyan) hover:text-pollen">
        Open swarm
        <ChevronRightIcon className="h-3.5 w-3.5" aria-hidden />
      </Link>
    </article>
  );
}

function WaggleRow({ item }: { item: WaggleFeedItem }) {
  return (
    <div className="flex gap-3">
      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-pollen shadow-[0_0_8px_rgba(253,185,39,0.5)]" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs text-(--qs-text-3)">
          <span className="text-pollen">{item.source_label}</span>
          <span aria-hidden>→</span>
          <span className="text-(--qs-purple-bright)">{item.target_label}</span>
          <span className="ml-auto">{formatFeedAgo(item.seconds_ago)}</span>
        </div>
        <p className="mt-1 text-sm text-(--qs-text-2)">{item.message}</p>
      </div>
    </div>
  );
}

export function SubSwarmsSection() {
  const { data, err } = useSwarmBoard();
  if (err) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-red)">Swarm board: {err}</p>
      </V4Card>
    );
  }
  if (!data) {
    return <div className="v4-swarm-grid">{["a", "b", "c", "d"].map((k) => <div key={k} className="v4-swarm-card h-36 animate-pulse bg-white/5" />)}</div>;
  }
  const syncMin = Math.max(1, Math.round(data.hive_sync_interval_sec / 60));
  return (
    <section>
      <div className="v4-section-title">
        <div>
          <h2>Sub-swarms</h2>
          <p className="desc">Decentralized swarms with local memory. Global sync roughly every {syncMin} min.</p>
        </div>
        <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4" aria-hidden />
          Resync
        </button>
      </div>
      {data.sub_swarms.length === 0 ? (
        <div className="v4-empty text-sm">No sub-swarms in the database — run bootstrap (scripts/hive_seed.py).</div>
      ) : (
        <div className="v4-swarm-grid">
          {data.sub_swarms.map((card) => (
            <SwarmCard key={card.id} card={card} />
          ))}
        </div>
      )}
    </section>
  );
}

export function WaggleFeedCard() {
  const { data, err } = useSwarmBoard();
  if (err) {
    return (
      <V4Card>
        <p className="text-sm text-(--qs-red)">{err}</p>
      </V4Card>
    );
  }
  if (!data) {
    return <V4Card className="h-48 animate-pulse bg-white/4"><span className="sr-only">Loading waggle feed</span></V4Card>;
  }
  return (
    <V4Card className="v4-card-interactive">
      <V4CardHeader
        title="Waggle dance feed"
        description="Signals across swarms — from hive tasks"
        as="h3"
        actions={<V4Badge tone="purple">{data.waggle_feed.length} new</V4Badge>}
      />
      {data.waggle_feed.length === 0 ? (
        <div className="v4-empty py-8 text-sm">No cross-swarm handoffs yet — create tasks or run a workflow.</div>
      ) : (
        <div className="flex flex-col gap-4">
          {data.waggle_feed.map((item) => (
            <WaggleRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </V4Card>
  );
}

/** @deprecated Use SubSwarmsSection + WaggleFeedCard */
export function SwarmBoardSection() {
  return (
    <div className="flex flex-col gap-10">
      <SubSwarmsSection />
      <WaggleFeedCard />
    </div>
  );
}
