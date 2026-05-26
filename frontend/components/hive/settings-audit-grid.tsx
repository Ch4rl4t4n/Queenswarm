"use client";

import { useMemo } from "react";

import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import {
  actionCategory,
  auditActorLabel,
  formatAuditAction,
  formatAuditTime,
  ipFromAuditPayload,
  type TenantAuditLogRow,
} from "@/lib/settings-audit-utils";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

function formatAuditDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function categoryTone(category: ReturnType<typeof actionCategory>): "gold" | "info" | "warn" | "ok" | "err" {
  switch (category) {
    case "auth":
      return "gold";
    case "keys":
      return "warn";
    case "sharing":
      return "info";
    default:
      return "ok";
  }
}

function targetSummary(row: TenantAuditLogRow): string {
  const parts: string[] = [];
  if (row.target_type) {
    parts.push(row.target_type.replaceAll("_", " "));
  }
  if (row.target_ref) {
    parts.push(row.target_ref.length > 48 ? `${row.target_ref.slice(0, 48)}…` : row.target_ref);
  }
  const sessionId = row.payload?.session_id;
  if (typeof sessionId === "string" && sessionId.length > 0) {
    parts.push(`session ${sessionId.slice(0, 12)}…`);
  }
  if (parts.length) {
    return parts.join(" · ");
  }
  const payloadKeys = Object.keys(row.payload ?? {});
  if (payloadKeys.length === 0) {
    return "No extra payload — action recorded for operator audit trail.";
  }
  return payloadKeys
    .slice(0, 4)
    .map((key) => {
      const value = row.payload[key];
      return `${key}=${String(value).slice(0, 40)}`;
    })
    .join(" · ");
}

interface AuditMarketCardProps {
  readonly row: TenantAuditLogRow;
  readonly memberMap: Map<string, string>;
}

function AuditMarketCard({ row, memberMap }: AuditMarketCardProps): JSX.Element {
  const category = actionCategory(row.action);
  const actor = auditActorLabel(row, memberMap);
  const actionLabel = formatAuditAction(row);
  const ip = ipFromAuditPayload(row.payload);

  return (
    <article className="v4-dream-cycle-card v4-audit-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">{actionLabel}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            {row.action.replaceAll("_", " ")}
          </p>
        </div>
        <V4Badge tone={categoryTone(category)}>{category}</V4Badge>
      </div>

      <div className="v4-audit-card-context">
        <p className="v4-field-label text-[10px] text-cyan-300/90">Who & what</p>
        <p className="mt-1 text-xs leading-relaxed text-(--qs-text-2)">
          <span className="text-(--qs-text-2)">{actor}</span>
          <span className="text-(--qs-text-3)"> · </span>
          <span className="text-(--qs-text-2)">{actionLabel}</span>
        </p>
        <p className="mt-2 text-xs leading-relaxed text-(--qs-text-3)">{targetSummary(row)}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        {formatAuditTime(row.created_at)} · {formatAuditDateTime(row.created_at)}
      </p>

      <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-(--qs-text-3)">
        <span className="text-(--qs-text-2)">{actor}</span>
        <span aria-hidden>·</span>
        <span className="font-mono text-[10px]">IP {ip}</span>
      </div>
    </article>
  );
}

interface SettingsAuditGridProps {
  readonly rows: TenantAuditLogRow[];
  readonly memberMap: Map<string, string>;
}

/** Marketplace-style 2×2 audit cards with bottom pagination. */
export function SettingsAuditGrid({ rows, memberMap }: SettingsAuditGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(() => rows.map((row) => row.id).join("|"), [rows]);
  const pagination = usePaginatedSlice(rows, pageSize, `${resetKey}|${pageSize}|${rows.length}`);

  return (
    <ViewportBoundedPanel
      className="v4-recipe-catalog-panel mt-4"
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
        {pagination.slice.map((row) => (
          <AuditMarketCard key={row.id} row={row} memberMap={memberMap} />
        ))}
      </div>
    </ViewportBoundedPanel>
  );
}

/** Skeleton grid while audit rows load. */
export function SettingsAuditGridSkeleton(): JSX.Element {
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className={cn("v4-dream-cycle-card h-[220px] animate-pulse bg-white/5")} />
      ))}
    </div>
  );
}
