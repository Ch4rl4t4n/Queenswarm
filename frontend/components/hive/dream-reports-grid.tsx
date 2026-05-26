"use client";

import { Info, Loader2, Moon, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import {
  DreamReportInfoDialog,
  type DreamCycleRow,
} from "@/components/hive/dream-report-info-dialog";
import { ListPaginator, ViewportBoundedPanel } from "@/components/ui/list-paginator";
import { V4Badge } from "@/components/ui/v4";
import { useGridTwoRowPageSize } from "@/lib/use-grid-two-row-page-size";
import { usePaginatedSlice } from "@/lib/use-paginated-slice";
import { cn } from "@/lib/utils";

function cycleStatusTone(status: string): "ok" | "warn" | "err" | "info" {
  const s = status.toLowerCase();
  if (s.includes("complete") || s.includes("success")) {
    return "ok";
  }
  if (s.includes("fail") || s.includes("error")) {
    return "err";
  }
  if (s.includes("run") || s.includes("queue") || s.includes("pending")) {
    return "info";
  }
  return "warn";
}

function formatCycleTitle(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Dream cycle";
  }
  return date.toLocaleString("sk-SK", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function shortCycleId(id: string): string {
  return id.replace(/-/g, "").slice(0, 8).toUpperCase();
}

function cycleSummary(row: DreamCycleRow): string {
  return `Supervisor history consolidation — ${row.items_processed} signals scanned, ${row.items_consolidated} insights saved to HiveMind, ${row.items_deduplicated} duplicates merged.`;
}

interface DreamReportCardProps {
  readonly row: DreamCycleRow;
  readonly onInfo: (cycleId: string) => void;
}

function DreamReportCard({ row, onInfo }: DreamReportCardProps): JSX.Element {
  const failed = row.status.toLowerCase().includes("fail");

  return (
    <article className="v4-dream-cycle-card flex h-full flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="line-clamp-2 text-sm font-semibold text-(--qs-text)">{formatCycleTitle(row.started_at)}</p>
          <p className="font-mono text-[10px] uppercase tracking-[0.08em] text-(--qs-text-3)">
            cycle {shortCycleId(row.id)}
          </p>
        </div>
        <V4Badge tone={cycleStatusTone(row.status)}>{row.status}</V4Badge>
      </div>

      <div className="flex items-center gap-2 text-xs text-(--qs-text-3)">
        <Moon className="h-3.5 w-3.5 shrink-0 text-(--qs-purple-bright)" aria-hidden />
        <span>Nightly memory lane</span>
      </div>

      <div className="v4-dream-report-context">
        <p className="v4-field-label text-[10px] text-cyan-300/90">What this run captured</p>
        <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-(--qs-text-2)">{cycleSummary(row)}</p>
      </div>

      <p className="font-mono text-[11px] text-(--qs-text-3)">
        processed={row.items_processed} · consolidated=
        <span className="text-pollen">{row.items_consolidated}</span> · dedup=
        <span className="text-cyan">{row.items_deduplicated}</span>
      </p>

      <div className="mt-auto flex flex-wrap gap-2">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          onClick={() => onInfo(row.id)}
        >
          <Info className="h-3.5 w-3.5" aria-hidden />
          Info
        </button>
        {failed ? <V4Badge tone="err">needs review</V4Badge> : <V4Badge tone="ok">verified</V4Badge>}
      </div>
    </article>
  );
}

interface DreamReportsGridProps {
  readonly cycles: DreamCycleRow[];
  readonly clearBusy?: boolean;
  readonly onClear?: () => void;
}

/** Marketplace-style 2×2 dream report cards with bottom pagination. */
export function DreamReportsGrid({ cycles, clearBusy = false, onClear }: DreamReportsGridProps): JSX.Element {
  const pageSize = useGridTwoRowPageSize({ columns: 2 });
  const resetKey = useMemo(() => cycles.map((row) => row.id).join("|"), [cycles]);
  const pagination = usePaginatedSlice(cycles, pageSize, `${resetKey}|${pageSize}|${cycles.length}`);
  const [infoCycleId, setInfoCycleId] = useState<string | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);

  function openInfo(cycleId: string): void {
    setInfoCycleId(cycleId);
    setInfoOpen(true);
  }

  if (cycles.length === 0) {
    return <p className="v4-dream-empty">No dream reports yet.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="v4-field-label">Latest dream reports ({cycles.length})</p>
        {onClear ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
            disabled={clearBusy}
            onClick={onClear}
          >
            {clearBusy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            ) : (
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            )}
            Clear all dream sessions
          </button>
        ) : null}
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
          {pagination.slice.map((row) => (
            <DreamReportCard key={row.id} row={row} onInfo={openInfo} />
          ))}
        </div>
      </ViewportBoundedPanel>

      <DreamReportInfoDialog
        cycleId={infoCycleId}
        open={infoOpen}
        onOpenChange={(next) => {
          setInfoOpen(next);
          if (!next) {
            setInfoCycleId(null);
          }
        }}
      />
    </div>
  );
}

/** Skeleton grid while dream cycles load. */
export function DreamReportsGridSkeleton(): JSX.Element {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className={cn("v4-dream-cycle-card h-[220px] animate-pulse bg-white/5")} />
      ))}
    </div>
  );
}
