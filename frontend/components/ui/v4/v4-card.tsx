import type { LucideIcon } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { V4StatIconTone } from "@/components/ui/v4/v4-stat";

interface V4CardProps {
  children: ReactNode;
  className?: string;
  tight?: boolean;
  glow?: boolean;
  id?: string;
  /** Test hook — forwarded to the rendered section so e2e getByTestId works. */
  "data-testid"?: string;
}

/** Glass section container — Hive Control V4. */
export function V4Card({ children, className, tight, glow, id, ...rest }: V4CardProps) {
  return (
    <section
      id={id}
      data-testid={rest["data-testid"]}
      className={cn("v4-card", tight && "v4-card-tight", glow && "v4-card-glow", className)}
    >
      {children}
    </section>
  );
}

/** Lucide icons or Hive Control V4 custom SVG icons. */
export type V4CardHeaderIcon = LucideIcon | ComponentType<{ className?: string; size?: number }>;

const leadingIconToneClass: Record<V4StatIconTone, string> = {
  default: "",
  purple: "v4-card-header-leading-icon--purple",
  cyan: "v4-card-header-leading-icon--cyan",
  green: "v4-card-header-leading-icon--green",
};

interface V4CardHeaderProps {
  title: string;
  description?: ReactNode;
  kicker?: string;
  /** Inline info hint at end of description — use sectionHintNode() from inline-section-hint. */
  hint?: ReactNode;
  /** Decorative icon chip left of the title — never use `actions` for icons. */
  leadingIcon?: V4CardHeaderIcon;
  leadingIconTone?: V4StatIconTone;
  /** Toolbar actions (buttons, badges) — never the info hint. */
  actions?: ReactNode;
  as?: "h2" | "h3";
}

export function V4CardHeader({
  title,
  description,
  kicker,
  hint,
  leadingIcon: LeadingIcon,
  leadingIconTone = "default",
  actions,
  as = "h2",
}: V4CardHeaderProps) {
  const TitleTag = as;
  const showDescription = Boolean(description) || Boolean(hint);

  return (
    <div className="v4-card-header">
      <div className="v4-card-header-top">
        <div className="v4-card-header-leading-row min-w-0 flex-1">
          {LeadingIcon ? (
            <span
              className={cn("v4-card-header-leading-icon", leadingIconToneClass[leadingIconTone])}
              aria-hidden
            >
              <LeadingIcon className="h-4 w-4" size={16} />
            </span>
          ) : null}
          <div className="v4-card-header-title min-w-0 flex-1">
            {kicker ? <span className="v4-label-kicker">{kicker}</span> : null}
            <TitleTag>{title}</TitleTag>
          </div>
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
