"use client";

import Link from "next/link";
import { ChevronRightIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { HiveApiError, hiveGet } from "@/lib/api";
import type { SwarmBoardCard, SwarmBoardResponse, WaggleFeedItem } from "@/lib/hive-types";
import { cn } from "@/lib/utils";
import { HexNumberBadge, LANE_HEX_STROKE } from "@/components/hive/hex-metric-tile";

function laneCardTheme(lane: string): {
  badgeStroke: string;
  title: string;
  bar: string;
  metric: string;
} {
  const L = lane.toLowerCase();
  if (L === "scout") {
    return {
      badgeStroke: LANE_HEX_STROKE.scout,
      title: "text-cyan",
      bar: "bg-cyan",
      metric: "text-cyan",
    };
  }
  if (L === "eval") {
    return {
      badgeStroke: LANE_HEX_STROKE.eval,
      title: "text-pollen",
      bar: "bg-pollen",
      metric: "text-pollen",
    };
  }
  if (L === "sim") {
    return {
      badgeStroke: LANE_HEX_STROKE.sim,
      title: "text-alert",
      bar: "bg-alert",
      metric: "text-alert",
    };
  }
  return {
    badgeStroke: LANE_HEX_STROKE.action,
    title: "text-success",
    bar: "bg-success",
    metric: "text-success",
  };
}

function feedLanePill(lane: string): string {
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
  if (L === "action") {
    return "border-success/45 bg-success/[0.1] text-success";
  }
  if (L === "all") {
    return "border-zinc-500/40 bg-zinc-500/10 text-zinc-400";
  }
  return "border-lime-400/45 bg-lime-400/10 text-lime-300";
}

function formatPollenSpaced(n: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(Math.round(n));
}

function formatAgo(sec: number | null): string {
  if (sec == null) {
    return "no sync yet";
  }
  if (sec < 45) {
    return `${sec}s ago`;
  }
  const m = Math.floor(sec / 60);
  if (m < 90) {
    return `${m}m ago`;
  }
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

function formatFeedAgo(sec: number): string {
  if (sec < 90) {
    return `${sec}s ago`;
  }
  return formatAgo(sec);
}

function SwarmBoardCardView({ card }: { card: SwarmBoardCard }) {
  const theme = laneCardTheme(card.lane);
  return (
    <article className="flex flex-col rounded-2xl qs-rim bg-[#0c0c14]/95 p-5 shadow-[inset_0_0_0_1px_rgb(255_255_255/0.04)]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 gap-3">
          <HexNumberBadge
            value={card.member_count}
            strokeColor={theme.badgeStroke}
            glowColor={theme.badgeStroke}
            sizePx={52}
          />
          <div className="min-w-0">
            <h3 className={cn("font-[family-name:var(--font-poppins)] text-lg font-bold", theme.title)}>
              {card.display_name}
            </h3>
            <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs text-zinc-500">{card.description}</p>
          </div>
        </div>
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 qs-chip uppercase tracking-wide",
            card.is_active
              ? "border-success/40 bg-success/10 text-success"
              : "border-zinc-600 bg-zinc-800/60 text-zinc-500",
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", card.is_active ? "bg-success" : "bg-zinc-500")} aria-hidden />
          {card.is_active ? "Active" : "Idle"}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-4">
        <div>
          <p className="qs-meta-label text-zinc-500">Queen</p>
          <p className="mt-1 truncate font-[family-name:var(--font-poppins)] text-xs font-medium text-zinc-200">
            {card.queen_label}
          </p>
        </div>
        <div>
          <p className="qs-meta-label text-zinc-500">Pollen</p>
          <p className="mt-1 font-[family-name:var(--font-poppins)] text-xs font-semibold tabular-nums text-zinc-100">
            {formatPollenSpaced(card.total_pollen)}
          </p>
        </div>
        <div>
          <p className="qs-meta-label text-zinc-500">Perf</p>
          <p className={cn("mt-1 font-[family-name:var(--font-poppins)] text-xs font-semibold tabular-nums", theme.metric)}>
            {card.avg_performance_pct}%
          </p>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/55">
        <div className={cn("h-full rounded-full transition-all", theme.bar)} style={{ width: `${card.avg_performance_pct}%` }} />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.06] pt-4">
        <p className="font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
          Last sync: {formatAgo(card.last_sync_seconds_ago)}
        </p>
        <Link
          href="/#hive-live-swarm"
          className="inline-flex items-center gap-0.5 font-[family-name:var(--font-poppins)] text-xs font-semibold text-cyan hover:text-pollen"
        >
          Open swarm
          <ChevronRightIcon className="h-3.5 w-3.5" aria-hidden />
        </Link>
      </div>
    </article>
  );
}

function WaggleRow({ item }: { item: WaggleFeedItem }) {
  return (
    <li className="flex flex-col gap-2 border-b border-white/[0.06] py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full border px-2.5 py-0.5 qs-chip",
            feedLanePill(item.source_lane),
          )}
        >
          {item.source_label}
        </span>
        <span className="font-[family-name:var(--font-poppins)] text-sm text-zinc-600" aria-hidden>
          →
        </span>
        <span
          className={cn(
            "rounded-full border px-2.5 py-0.5 qs-chip",
            feedLanePill(item.target_lane),
          )}
        >
          {item.target_label}
        </span>
        <p className="w-full font-[family-name:var(--font-poppins)] text-sm text-zinc-300 sm:ml-2 sm:w-auto">
          {item.message}
        </p>
      </div>
      <p className="shrink-0 text-right font-[family-name:var(--font-poppins)] text-[11px] text-zinc-500">
        {formatFeedAgo(item.seconds_ago)}
      </p>
    </li>
  );
}

export function SwarmBoardSection() {
  const [data, setData] = useState<SwarmBoardResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function load(): Promise<void> {
      try {
        const board = await hiveGet<SwarmBoardResponse>("dashboard/swarm-board");
        if (alive) {
          setData(board);
          setErr(null);
        }
      } catch (e) {
        const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Swarm board unreachable";
        if (alive) {
          setErr(msg);
          setData(null);
        }
      }
    }
    void load();
    const id = window.setInterval(() => void load(), 60_000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  if (err) {
    return (
      <section className="rounded-3xl border border-danger/30 bg-danger/[0.06] p-6">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-danger">Swarm board: {err}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-10">
        <div>
          <div className="h-8 w-48 animate-pulse rounded-lg bg-white/10" />
          <div className="mt-2 h-4 w-96 max-w-full animate-pulse rounded bg-white/5" />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {["a", "b", "c", "d"].map((k) => (
            <div key={k} className="h-64 animate-pulse rounded-2xl bg-white/[0.04]" />
          ))}
        </div>
      </div>
    );
  }

  const syncMin = Math.max(1, Math.round(data.hive_sync_interval_sec / 60));

  return (
    <div className="flex flex-col gap-10">
      <section>
        <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="font-[family-name:var(--font-poppins)] text-2xl font-bold text-[#fafafa]">Sub-Swarms</h2>
            <p className="mt-2 max-w-2xl font-[family-name:var(--font-poppins)] text-sm text-zinc-500">
              Four decentralized swarms with local memory. Global sync roughly every {syncMin} min.
            </p>
          </div>
        </div>
        {data.sub_swarms.length === 0 ? (
          <p className="mt-6 rounded-xl border border-alert/25 bg-alert/[0.06] p-4 text-sm text-zinc-400">
            No sub-swarms in the database — run bootstrap (e.g. <span className="text-cyan/80">scripts/hive_seed.py</span>).
          </p>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {data.sub_swarms.map((card) => (
              <SwarmBoardCardView key={card.id} card={card} />
            ))}
          </div>
        )}
      </section>

      <section className="rounded-3xl border-[2px] border-magenta/20 bg-[#08080f]/95 p-6 shadow-[0_0_40px_rgb(255_0_170/0.08)] md:p-8">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="font-[family-name:var(--font-poppins)] text-xl font-semibold text-[#fafafa]">
            Waggle Dance Feed
          </h2>
          <p className="font-[family-name:var(--font-poppins)] text-xs text-zinc-500">Signals across swarms · from hive tasks</p>
        </div>
        {data.waggle_feed.length === 0 ? (
          <p className="mt-6 text-center font-[family-name:var(--font-poppins)] text-sm text-zinc-600">
            No cross-swarm handoffs yet — create tasks or run a workflow.
          </p>
        ) : (
          <ul className="mt-4 rounded-2xl qs-rim bg-black/35 px-4 md:px-6">
            {data.waggle_feed.map((item) => (
              <WaggleRow key={item.id} item={item} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
