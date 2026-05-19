import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4StatGridProps {
  children: ReactNode;
  className?: string;
}

/** KPI stat row — 1 col mobile · 2 col tablet · 4 col desktop (see globals.css). */
export function V4StatGrid({ children, className }: V4StatGridProps) {
  return <div className={cn("v4-stat-grid", className)}>{children}</div>;
}
