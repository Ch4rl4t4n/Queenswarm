"use client";

import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export type StatusTone = "online" | "idle" | "error" | "offline";

interface StatusIndicatorProps extends HTMLAttributes<HTMLSpanElement> {
  tone: StatusTone;
  label?: string;
  pulse?: boolean;
}

const TONE_STYLES: Record<
  StatusTone,
  { dot: string; ring: string; label: string }
> = {
  online: {
    dot: "bg-success shadow-[0_0_10px_#00FF88]",
    ring: "ring-success/45",
    label: "text-success",
  },
  idle: {
    dot: "bg-data shadow-[0_0_8px_rgba(0,255,255,0.55)]",
    ring: "ring-data/35",
    label: "text-data",
  },
  error: {
    dot: "bg-danger shadow-[0_0_10px_#FF3366]",
    ring: "ring-danger/45",
    label: "text-danger",
  },
  offline: {
    dot: "bg-zinc-600 shadow-none",
    ring: "ring-zinc-500/40",
    label: "text-zinc-400",
  },
};

/** Hive status lamp — WCAG via paired text; motion respects prefers-reduced-motion. */
export function StatusIndicator({ tone, label, className, pulse = true, ...rest }: StatusIndicatorProps) {
  const styles = TONE_STYLES[tone];
  const animate =
    pulse && tone === "online"
      ? "motion-safe:animate-[pulse-slow_2.4s_ease-in-out_infinite]"
      : "";

  return (
    <span className={cn("inline-flex items-center gap-2", className)} {...rest}>
      <span
        className={cn(
          "relative inline-flex h-2.5 w-2.5 shrink-0 rounded-full ring-2 ring-offset-2 ring-offset-[#050510]",
          styles.dot,
          styles.ring,
          animate,
        )}
        aria-hidden
      />
      {label ? (
        <span className={cn("font-[family-name:var(--font-poppins)] text-xs font-medium", styles.label)}>
          {label}
        </span>
      ) : null}
    </span>
  );
}
