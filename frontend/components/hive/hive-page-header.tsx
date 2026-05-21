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
  /** Green “Hive open / synced” pill (V4 page header). */
  status?: ReactNode;
  info?: {
    title: MaybeLocalizedString;
    description: MaybeLocalizedString;
    options?: MaybeLocalizedStringList;
  };
  className?: string;
}

/** Consistent cockpit header — Hive Control V4 page-header layout. */
export function HivePageHeader({ title, subtitle, actions, status, info, className }: HivePageHeaderProps) {
  return (
    <header className={cn("qs-page-header mb-5 flex flex-col gap-3 lg:mb-6 lg:gap-4", className)}>
      <div className="page-header-top flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <h1 className="truncate">{title}</h1>
          {info ? <InfoHint title={info.title} description={info.description} options={info.options} /> : null}
        </div>
        {status ? <div className="page-header-end flex shrink-0 items-center">{status}</div> : null}
      </div>
      {subtitle ? (
        <div className="description max-w-2xl font-(family-name:--font-poppins) text-[15px] leading-relaxed text-(--qs-text-3)">
          {subtitle}
        </div>
      ) : null}
      {actions ? <div className="page-actions flex flex-wrap items-center gap-3">{actions}</div> : null}
    </header>
  );
}
