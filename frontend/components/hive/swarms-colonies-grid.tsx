"use client";

import { Eye, Pause, Pencil, Play } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge, V4IconPollen } from "@/components/ui/v4";
import type { SwarmsOverviewColony } from "@/lib/hive-types";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

function formatPollen(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return String(Math.round(n * 10) / 10);
}

function formatAgo(sec: number | null): string {
  if (sec == null) return "awaiting sync";
  if (sec < 60) return `${sec}s ago`;
  const m = Math.floor(sec / 60);
  if (m < 90) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function healthTone(severity: "info" | "warn" | "error"): "ok" | "warn" | "err" {
  if (severity === "error") return "err";
  if (severity === "warn") return "warn";
  return "ok";
}

interface ColonyMarketCardProps {
  readonly colony: SwarmsOverviewColony;
  readonly syncMin: number;
  readonly busy: string | null;
  readonly selected: boolean;
  readonly onTogglePause: (colony: SwarmsOverviewColony) => void;
  readonly onOpen: (colony: SwarmsOverviewColony) => void;
}

function ColonyMarketCard({
  colony,
  syncMin,
  busy,
  selected,
  onTogglePause,
  onOpen,
}: ColonyMarketCardProps): JSX.Element {
  const pauseBusy = busy === `pause-${colony.id}`;

  return (
    <article
      className={cn(
        "v4-dream-cycle-card flex h-full flex-col gap-3",
        selected && "ring-1 ring-(--qs-amber)/50",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-(--qs-text)">
            <span className="truncate">{colony.display_name}</span>
            {colony.health ? (
              <span
                title={`${colony.health.open_count} note${colony.health.open_count === 1 ? "" : "s"} · ${colony.health.last_message}`}
                className={cn(
                  "inline-block h-2 w-2 shrink-0 rounded-full",
                  colony.health.last_severity === "error" && "bg-(--qs-red) shadow-[0_0_6px_var(--qs-red)]",
                  colony.health.last_severity === "warn" && "bg-pollen shadow-[0_0_6px_var(--qs-pollen)]",
                  colony.health.last_severity === "info" && "bg-(--qs-cyan)",
                )}
                aria-label={`${colony.health.open_count} open health note(s)`}
              />
            ) : null}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">{colony.lane_label}</p>
        </div>
        <V4Badge tone={colony.status === "active" ? "ok" : "warn"}>{colony.status}</V4Badge>
      </div>

      <p className="text-xs leading-relaxed text-(--qs-text-3)">
        Sub-swarm <span className="font-mono text-(--qs-text-2)">{colony.slug}</span> — queen{" "}
        <span className="text-(--qs-text-2)">{colony.queen_label}</span> orchestrates {colony.member_count} bee
        {colony.member_count === 1 ? "" : "s"} with local LangGraph memory.
      </p>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">How this colony runs</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          Decentralized sub-hive with local hive mind; global sync every {syncMin} min. Maynard-Cross pollen rewards
          apply to verified outcomes only.
        </p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {colony.slug} · 👑 {colony.queen_label} · {colony.member_count} bees
      </p>

      <div className="flex flex-wrap gap-2">
        <V4Badge tone="purple">{colony.lane_label}</V4Badge>
        <span className="v4-pollen-pill inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px]">
          <V4IconPollen size={11} />
          {formatPollen(colony.total_pollen)}
        </span>
        <V4Badge tone="info">{formatAgo(colony.last_sync_seconds_ago)}</V4Badge>
        {colony.health && colony.health.open_count > 0 ? (
          <V4Badge tone={healthTone(colony.health.last_severity)}>
            {colony.health.open_count} health note{colony.health.open_count === 1 ? "" : "s"}
          </V4Badge>
        ) : null}
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--primary qs-btn--sm gap-1.5"
          onClick={() => onOpen(colony)}
        >
          <Eye className="h-3.5 w-3.5" aria-hidden />
          {selected ? "Close" : "Open"}
        </button>
        {colony.queen_agent_id ? (
          <Link
            href={`/agents/${encodeURIComponent(colony.queen_agent_id)}/edit`}
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            title="Edit manager system prompt + tools"
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden />
            Edit policy
          </Link>
        ) : null}
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={pauseBusy}
          onClick={() => onTogglePause(colony)}
        >
          {colony.status === "paused" ? (
            <Play className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <Pause className="h-3.5 w-3.5" aria-hidden />
          )}
          {colony.status === "paused" ? "Resume" : "Pause"}
        </button>
      </div>
    </article>
  );
}

interface SwarmsColoniesGridProps {
  readonly colonies: SwarmsOverviewColony[];
  readonly syncMin: number;
  readonly busy: string | null;
  readonly openColonyId: string | null;
  readonly onTogglePause: (colony: SwarmsOverviewColony) => void;
  readonly onOpenColony: (colony: SwarmsOverviewColony) => void;
}

/** Marketplace-style 2×2 colony cards with bottom pagination (no inner scroll). */
export function SwarmsColoniesGrid({
  colonies,
  syncMin,
  busy,
  openColonyId,
  onTogglePause,
  onOpenColony,
}: SwarmsColoniesGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(
    () => colonies.map((c) => `${c.id}:${c.status}:${c.member_count}`).join("|"),
    [colonies],
  );
  const pagination = usePaginatedSlice(colonies, pageSize, `${resetKey}|${pageSize}|${colonies.length}`);

  if (colonies.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-(--qs-text-3)">
        No colonies yet — create one with <strong className="text-pollen">New colony</strong>.
      </p>
    );
  }

  return (
    <ViewportBoundedPanel
      className="v4-recipe-catalog-panel"
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
      <div className="grid gap-3 md:grid-cols-2">
        {pagination.slice.map((colony) => (
          <ColonyMarketCard
            key={colony.id}
            colony={colony}
            syncMin={syncMin}
            busy={busy}
            selected={openColonyId === colony.id}
            onTogglePause={onTogglePause}
            onOpen={onOpenColony}
          />
        ))}
      </div>
    </ViewportBoundedPanel>
  );
}
