import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ResponsiveTableProps {
  /** Full-width data table — shown from `md` (768px) upward. */
  table: ReactNode;
  /** Stacked card/list fallback — shown below `md`. */
  cards: ReactNode;
  className?: string;
}

/**
 * Desktop/tablet table with a mobile card fallback — avoids horizontal squash on phones.
 */
export function ResponsiveTable({ table, cards, className }: ResponsiveTableProps) {
  return (
    <>
      <div className={cn("hidden hive-scrollbar overflow-x-auto md:block", className)}>{table}</div>
      <div className={cn("flex flex-col gap-3 md:hidden", className)}>{cards}</div>
    </>
  );
}
