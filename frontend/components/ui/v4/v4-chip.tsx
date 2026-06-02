import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4ChipProps {
  children: ReactNode;
  active?: boolean;
  count?: number | string;
  onClick?: () => void;
  className?: string;
  type?: "button" | "span";
  /** `tag` = read-only keyword pill with ellipsis containment. */
  variant?: "filter" | "tag";
  title?: string;
}

/** Filter / lane pill — Hive Control V4. */
export function V4Chip({
  children,
  active,
  count,
  onClick,
  className,
  type = "button",
  variant = "filter",
  title,
}: V4ChipProps) {
  const cls = cn(
    "v4-chip",
    variant === "tag" && "v4-chip--tag",
    active && "v4-chip--active",
    className,
  );
  const content = (
    <>
      <span className="v4-chip__label">{children}</span>
      {count !== undefined ? <span className="v4-chip-count">{count}</span> : null}
    </>
  );
  if (type === "span" || !onClick) {
    return (
      <span className={cls} title={title}>
        {content}
      </span>
    );
  }
  return (
    <button type="button" className={cls} onClick={onClick} title={title}>
      {content}
    </button>
  );
}
