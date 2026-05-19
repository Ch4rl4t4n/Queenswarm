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
  actions?: ReactNode;
  as?: "h2" | "h3";
}

export function V4CardHeader({ title, description, kicker, actions, as = "h2" }: V4CardHeaderProps) {
  const TitleTag = as;
  return (
    <div className="v4-card-header">
      <div className="min-w-0">
        {kicker ? <span className="v4-label-kicker">{kicker}</span> : null}
        <TitleTag>{title}</TitleTag>
        {description ? <p className="desc">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
