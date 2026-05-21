"use client";

import { RefreshCw } from "lucide-react";
import type { JSX } from "react";

import { cn } from "@/lib/utils";

interface AgentsPageSyncBannerProps {
  rosterSyncPending?: boolean;
  rosterError?: string | null;
  swarmsError?: string | null;
  onRetry?: () => void;
  retryBusy?: boolean;
  className?: string;
}

/** Unified degraded-state banner for the Agents control plane. */
export function AgentsPageSyncBanner({
  rosterSyncPending = false,
  rosterError = null,
  swarmsError = null,
  onRetry,
  retryBusy = false,
  className,
}: AgentsPageSyncBannerProps): JSX.Element | null {
  const message =
    rosterError ??
    swarmsError ??
    (rosterSyncPending ? "Agent ledger syncing — live poll will retry shortly." : null);

  if (!message) {
    return null;
  }

  const isError = Boolean(rosterError || swarmsError);

  return (
    <div
      role="status"
      data-testid="agents-sync-banner"
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm",
        isError ? "border-(--qs-red)/40 bg-(--qs-red)/10 text-(--qs-text-2)" : "border-alert/30 bg-alert/10 text-(--qs-text-2)",
        className,
      )}
    >
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="qs-btn qs-btn--ghost qs-btn--sm gap-1.5"
          disabled={retryBusy}
          onClick={onRetry}
        >
          <RefreshCw className={cn("h-3.5 w-3.5", retryBusy && "animate-spin")} aria-hidden />
          Retry sync
        </button>
      ) : null}
    </div>
  );
}
