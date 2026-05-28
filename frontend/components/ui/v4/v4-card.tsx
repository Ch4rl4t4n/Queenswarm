import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4CardProps {
  children: ReactNode;
  className?: string;
  tight?: boolean;
  glow?: boolean;
  id?: string;
}

/** Glass section container — Hive Control V4. */
export function V4Card({ children, className, tight, glow, id }: V4CardProps) {
  return (
    <section id={id} className={cn("v4-card", tight && "v4-card-tight", glow && "v4-card-glow", className)}>
      {children}
    </section>
  );
}

interface V4CardHeaderProps {
  title: string;
  description?: ReactNode;
  kicker?: string;
  /** Inline info hint at end of description — use sectionHintNode() from inline-section-hint. */
  hint?: ReactNode;
  /** Toolbar actions (buttons, badges) — never the info hint. */
  actions?: ReactNode;
  as?: "h2" | "h3";
}

export function V4CardHeader({ title, description, kicker, hint, actions, as = "h2" }: V4CardHeaderProps) {
  const TitleTag = as;
  const showDescription = Boolean(description) || Boolean(hint);

  return (
    <div className="v4-card-header">
      <div className="v4-card-header-top">
        <div className="v4-card-header-title min-w-0 flex-1">
          {kicker ? <span className="v4-label-kicker">{kicker}</span> : null}
          <TitleTag>{title}</TitleTag>
        </div>
        {actions ? (
          <div className="v4-card-header-actions flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
      {showDescription ? (
        <p className="desc v4-card-header-desc">
          {description}
          {hint}
        </p>
      ) : null}
    </div>
  );
}
