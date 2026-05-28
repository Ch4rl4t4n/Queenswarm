import type { ReactNode } from "react";

import { InlineSectionHint } from "@/components/hive/inline-section-hint";
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
    manualHref?: string;
  };
  className?: string;
}

/** Consistent cockpit header — title, description with inline hint, then content. */
export function HivePageHeader({ title, subtitle, actions, status, info, className }: HivePageHeaderProps) {
  const showDescription = Boolean(subtitle) || Boolean(info);

  return (
    <header className={cn("qs-page-header mb-4 flex flex-col gap-2 lg:mb-5 lg:gap-2", className)}>
      <div className="page-header-top flex items-start justify-between gap-3">
        <h1 className="min-w-0 flex-1 text-balance">{title}</h1>
        {status ? <div className="page-header-end flex shrink-0 items-center">{status}</div> : null}
      </div>
      {showDescription ? (
        <p className="description w-full max-w-none font-(family-name:--font-poppins) text-[15px] leading-snug text-(--qs-text-3) lg:leading-normal">
          {subtitle}
          {info ? (
            <InlineSectionHint
              title={info.title}
              description={info.description}
              options={info.options}
              manualHref={info.manualHref}
            />
          ) : null}
        </p>
      ) : null}
      {actions ? <div className="page-actions flex flex-wrap items-center gap-3">{actions}</div> : null}
    </header>
  );
}
