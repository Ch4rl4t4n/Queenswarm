import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface HivePageHeaderProps {
  /** Main page title — Poppins. */
  title: string;
  /** Muted subtitle under the title. */
  subtitle?: ReactNode;
  /** Optional right-aligned actions (buttons, pills). */
  actions?: ReactNode;
  className?: string;
}

/** Consistent cockpit header aligned with QueenSwarm Figma mocks. */
export function HivePageHeader({ title, subtitle, actions, className }: HivePageHeaderProps) {
  return (
    <header className={cn("qs-page-header flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="space-y-2">
        <h1>{title}</h1>
        {subtitle ? (
          <div className="description max-w-2xl font-[family-name:var(--font-poppins)] text-sm leading-relaxed text-muted-foreground">
            {subtitle}
          </div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
