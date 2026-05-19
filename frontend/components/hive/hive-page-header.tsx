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
    <header
      className={cn(
        "qs-page-header mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between",
        className,
      )}
    >
      <div className="page-title min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <h1>{title}</h1>
          {info ? <InfoHint title={info.title} description={info.description} options={info.options} /> : null}
        </div>
        {subtitle ? (
          <div className="description max-w-2xl font-(family-name:--font-poppins) text-[15px] leading-relaxed text-(--qs-text-3)">
            {subtitle}
          </div>
        ) : null}
      </div>
      <div className="page-actions flex shrink-0 flex-wrap items-center gap-3">
        {actions}
        {status ? <div className="v4-status-pill">{status}</div> : null}
      </div>
    </header>
  );
}
