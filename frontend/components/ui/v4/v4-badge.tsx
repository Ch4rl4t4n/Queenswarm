import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type V4BadgeTone = "ok" | "warn" | "err" | "info" | "gold" | "purple";

interface V4BadgeProps {
  children: ReactNode;
  tone?: V4BadgeTone;
  className?: string;
}

const toneClass: Record<V4BadgeTone, string> = {
  ok: "v4-badge--ok",
  warn: "v4-badge--warn",
  err: "v4-badge--err",
  info: "v4-badge--info",
  gold: "v4-badge--gold",
  purple: "v4-badge--purple",
};

/** Status / lane badge — Hive Control V4. */
export function V4Badge({ children, tone = "ok", className }: V4BadgeProps) {
  return <span className={cn("v4-badge", toneClass[tone], className)}>{children}</span>;
}
