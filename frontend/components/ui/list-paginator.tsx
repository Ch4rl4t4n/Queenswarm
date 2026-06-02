"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

interface ListPaginatorProps {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  className?: string;
}

function pageNumbers(current: number, total: number): number[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages = new Set<number>([1, total, current, current - 1, current + 1]);
  return [...pages].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);
}

/** Compact numbered pagination bar for viewport-bounded lists. */
export function ListPaginator({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  className,
}: ListPaginatorProps): JSX.Element | null {
  if (totalPages <= 1) {
    return null;
  }

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);
  const numbers = pageNumbers(page, totalPages);

  return (
    <div
      className={cn(
        "v4-viewport-panel-footer flex flex-col items-stretch gap-3 max-lg:gap-2.5 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between",
        className,
      )}
    >
      <p className="text-xs text-(--qs-text-3)">
        {start}–{end} of {totalItems}
      </p>
      <nav className="flex flex-wrap items-center gap-1" aria-label="Pagination">
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm px-2"
          disabled={page <= 1}
          aria-label="Previous page"
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden />
        </button>
        {numbers.map((num, idx) => {
          const prev = numbers[idx - 1];
          const gap = prev != null && num - prev > 1;
          return (
            <span key={num} className="inline-flex items-center gap-1">
              {gap ? <span className="px-1 text-xs text-(--qs-text-4)">…</span> : null}
              <button
                type="button"
                className={cn(
                  "min-w-8 rounded-md px-2 py-1 text-xs font-medium transition",
                  num === page
                    ? "bg-pollen/20 text-pollen shadow-[0_0_12px_rgb(253_185_39/0.2)]"
                    : "text-(--qs-text-3) hover:bg-white/5 hover:text-(--qs-text)",
                )}
                aria-current={num === page ? "page" : undefined}
                onClick={() => onPageChange(num)}
              >
                {num}
              </button>
            </span>
          );
        })}
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm px-2"
          disabled={page >= totalPages}
          aria-label="Next page"
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </nav>
    </div>
  );
}

interface ViewportBoundedPanelProps {
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  scrollable?: boolean;
}

/** Fixed viewport-height panel — content stays within the current screen (desktop). */
export function ViewportBoundedPanel({
  children,
  footer,
  className,
  scrollable = false,
}: ViewportBoundedPanelProps): JSX.Element {
  return (
    <div className={cn("v4-viewport-panel v4-viewport-panel--page-scroll", className)} data-hive-viewport-panel="">
      <div
        className={cn("v4-viewport-panel-body hive-scrollbar", scrollable && "overflow-y-auto")}
        data-hive-viewport-panel-body=""
      >
        {children}
      </div>
      {footer}
    </div>
  );
}
