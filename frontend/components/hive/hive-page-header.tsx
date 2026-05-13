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
    <header className={cn("flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="space-y-2">
        <h1 className="font-[family-name:var(--font-poppins)] text-2xl font-semibold tracking-tight text-[#fafafa] sm:text-3xl md:text-4xl">
          {title}
        </h1>
        {subtitle ? (
          <div className="max-w-2xl font-[family-name:var(--font-inter)] text-sm leading-relaxed text-muted-foreground">
            {subtitle}
          </div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
