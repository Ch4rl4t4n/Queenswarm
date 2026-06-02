"use client";

import { RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";

interface HiveRefreshButtonProps {
  onClick?: () => void | Promise<void>;
  disabled?: boolean;
  /** When true, icon spins and button is disabled. */
  busy?: boolean;
  /** Visible label — default "Refresh". */
  label?: string;
  className?: string;
  type?: "button" | "submit";
}

/** Standard refresh control — top-right of panels; icon-only ≤1023px, icon + label on desktop. */
export function HiveRefreshButton({
  onClick,
  disabled = false,
  busy = false,
  label = "Refresh",
  className,
  type = "button",
}: HiveRefreshButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "hive-refresh-btn qs-btn qs-btn--ghost qs-btn--sm shrink-0 touch-manipulation",
        className,
      )}
      disabled={disabled || busy}
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      <RefreshCw className={cn("size-4 shrink-0", busy && "animate-spin")} aria-hidden />
      <span className="hive-refresh-btn__label">{label}</span>
    </button>
  );
}
