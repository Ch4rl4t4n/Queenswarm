"use client";

import { RefreshCw } from "lucide-react";

import type { HivePageShellErrorProps } from "@/lib/hive-page-error";
import { cn } from "@/lib/utils";

type HivePageErrorBannerProps = HivePageShellErrorProps;

/** Inline alert strip — errors, warnings, optional retry (Phase 8.2 / v2.1). */
export function HivePageErrorBanner({
  message,
  tone = "error",
  onDismiss,
  onRetry,
  retryBusy = false,
  testId,
}: HivePageErrorBannerProps) {
  const isError = tone === "error";

  return (
    <div
      data-testid={testId}
      className={cn(
        "flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-xl border px-3 py-2 text-xs",
        isError
          ? "border-(--qs-red)/35 bg-(--qs-red)/10 text-(--qs-red)"
          : "border-alert/30 bg-alert/10 text-(--qs-text-2)",
      )}
      role={isError ? "alert" : "status"}
    >
      <span>{message}</span>
      <div className="flex shrink-0 items-center gap-1">
        {onRetry ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 gap-1.5"
            disabled={retryBusy}
            onClick={onRetry}
          >
            <RefreshCw className={cn("size-3.5", retryBusy && "animate-spin")} aria-hidden />
            Retry sync
          </button>
        ) : null}
        {onDismiss ? (
          <button
            type="button"
            className="qs-btn qs-btn--ghost qs-btn--sm shrink-0"
            aria-label="Dismiss error"
            onClick={onDismiss}
          >
            Dismiss
          </button>
        ) : null}
      </div>
    </div>
  );
}
