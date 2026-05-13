"use client";

import { cn } from "@/lib/utils";

export type ProgressVariant = "pollen" | "data" | "success" | "alert";

interface ProgressBarProps {
  value: number;
  /** 0–100 clamped visually */
  max?: number;
  variant?: ProgressVariant;
  className?: string;
  label?: string;
}

const TRACK: Record<ProgressVariant, string> = {
  pollen: "from-pollen/90 via-[#ffd454] to-data",
  data: "from-data via-cyan-300 to-emerald-400",
  success: "from-success via-emerald-300 to-teal-400",
  alert: "from-alert via-fuchsia-400 to-danger",
};

/** Gradient fill with shimmer overlay (motion-safe only). */
export function ProgressBar({
  value,
  max = 100,
  variant = "pollen",
  className,
  label,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn("w-full space-y-1", className)}>
      {label ? (
        <p className="font-[family-name:var(--font-poppins)] text-[10px] uppercase tracking-[0.18em] text-cyan/75">
          {label}
        </p>
      ) : null}
      <div
        className="relative h-2.5 w-full overflow-hidden rounded-full border border-cyan/15 bg-black/50"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn(
            "relative h-full rounded-full bg-gradient-to-r",
            TRACK[variant],
          )}
          style={{ width: `${pct}%` }}
        >
          <span className="pointer-events-none absolute inset-0 overflow-hidden rounded-full">
            <span className="absolute inset-0 bg-[linear-gradient(110deg,transparent,rgba(255,255,255,0.32),transparent)] opacity-70 motion-safe:animate-[shimmer-overlay_2s_linear_infinite]" />
          </span>
        </div>
      </div>
    </div>
  );
}
