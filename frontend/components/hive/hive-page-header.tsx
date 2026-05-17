import type { ReactNode } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import type { MaybeLocalizedString, MaybeLocalizedStringList } from "@/lib/ui-language";
import { cn } from "@/lib/utils";

interface HivePageHeaderProps {
  /** Main page title — Poppins. */
  title: string;
  /** Muted subtitle under the title. */
  subtitle?: ReactNode;
  /** Optional right-aligned actions (buttons, pills). */
  actions?: ReactNode;
  info?: {
    title: MaybeLocalizedString;
    description: MaybeLocalizedString;
    options?: MaybeLocalizedStringList;
  };
  className?: string;
}

/** Consistent cockpit header aligned with QueenSwarm Figma mocks. */
export function HivePageHeader({ title, subtitle, actions, info, className }: HivePageHeaderProps) {
  return (
    <header className={cn("qs-page-header flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <h1>{title}</h1>
          {info ? <InfoHint title={info.title} description={info.description} options={info.options} /> : null}
        </div>
        {subtitle ? (
          <div className="description max-w-2xl font-(family-name:--font-poppins) text-sm leading-relaxed text-muted-foreground">
            {subtitle}
          </div>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
