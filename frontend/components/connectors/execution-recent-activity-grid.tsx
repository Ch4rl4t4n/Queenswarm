"use client";

import { Loader2, Trash2 } from "lucide-react";
import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

export interface ExecutionActivityRow {
  readonly event_type: string;
  readonly message: string;
  readonly at: string;
  readonly payload?: Record<string, unknown>;
}

function eventTypeLabel(eventType: string): string {
  return eventType.replaceAll("_", " ");
}

function eventTypeCategory(eventType: string): string {
  return eventType.replaceAll("_", " ").toUpperCase();
}

function eventTone(eventType: string): "ok" | "warn" | "err" | "info" | "gold" {
  const normalized = eventType.trim().toLowerCase();
  if (normalized === "approval_cleared" || normalized === "tool_execute") {
    return "ok";
  }
  if (normalized === "digest_preview_send") {
    return "gold";
  }
  if (normalized.includes("error") || normalized.includes("failed")) {
    return "err";
  }
  if (normalized.includes("pending") || normalized.includes("proposal")) {
    return "warn";
  }
  return "info";
}

function formatActivityAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function payloadSummary(payload: Record<string, unknown> | undefined): string {
  if (!payload || Object.keys(payload).length === 0) {
    return "No extra payload — event recorded for operator audit trail.";
  }
  const parts: string[] = [];
  if (typeof payload.connector_slug === "string") {
    parts.push(`connector ${payload.connector_slug}`);
  }
  if (typeof payload.lane === "string") {
    parts.push(`lane ${payload.lane}`);
  }
  if (typeof payload.tool_name === "string") {
    parts.push(`tool ${payload.tool_name}`);
  }
  if (typeof payload.proposal_id === "string") {
    parts.push(`proposal ${payload.proposal_id.slice(0, 8)}…`);
  }
  if (parts.length) {
    return parts.join(" · ");
  }
  return Object.entries(payload)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${String(value).slice(0, 48)}`)
    .join(" · ");
}

function activityKey(item: ExecutionActivityRow): string {
  return `${item.at}-${item.event_type}-${item.message.slice(0, 24)}`;
}

interface ActivityMarketCardProps {
  readonly item: ExecutionActivityRow;
}

function ActivityMarketCard({ item }: ActivityMarketCardProps): JSX.Element {
  const isDigest = item.event_type === "digest_preview_send";

  return (
    <article
      className={cn(
        "v4-dream-cycle-card flex h-full flex-col gap-3",
        isDigest && "border-pollen/25",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className={cn("line-clamp-2 text-sm font-semibold", isDigest ? "text-pollen" : "text-(--qs-text)")}>
            {item.message}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {eventTypeCategory(item.event_type)}
          </p>
        </div>
        <V4Badge tone={eventTone(item.event_type)}>{eventTypeLabel(item.event_type)}</V4Badge>
      </div>

      <p className="line-clamp-3 text-xs leading-relaxed text-(--qs-text-3)">{item.message}</p>

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Execution context</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">{payloadSummary(item.payload)}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {item.event_type} · {formatActivityAt(item.at)}
      </p>

      <div className="v4-dream-cycle-card-actions">
        <V4Badge tone={eventTone(item.event_type)}>{eventTypeLabel(item.event_type)}</V4Badge>
        {isDigest ? <V4Badge tone="gold">digest</V4Badge> : null}
        {item.payload?.pending_cleared === true ? <V4Badge tone="ok">cleared</V4Badge> : null}
      </div>
    </article>
  );
}

interface ExecutionRecentActivityGridProps {
  readonly items: ExecutionActivityRow[];
  readonly clearBusy: boolean;
  readonly onClear: () => void;
}

/** Marketplace-style 2×2 recent activity cards with bottom pagination. */
export function ExecutionRecentActivityGrid({
  items,
  clearBusy,
  onClear,
}: ExecutionRecentActivityGridProps): JSX.Element | null {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(
    () => items.map((row) => `${row.at}:${row.event_type}:${row.message.slice(0, 16)}`).join("|"),
    [items],
  );
  const pagination = usePaginatedSlice(items, pageSize, `${resetKey}|${pageSize}|${items.length}`);

  if (items.length === 0) {
    return null;
  }

  return (
    <div className="shrink-0 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="v4-field-label">Recent activity ({items.length})</p>
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={clearBusy}
          onClick={onClear}
        >
          {clearBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Trash2 className="h-3.5 w-3.5" aria-hidden />}
          Clear recent activities
        </button>
      </div>

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
          {pagination.slice.map((item) => (
            <ActivityMarketCard key={activityKey(item)} item={item} />
          ))}
        </div>
      </ViewportBoundedPanel>
    </div>
  );
}
