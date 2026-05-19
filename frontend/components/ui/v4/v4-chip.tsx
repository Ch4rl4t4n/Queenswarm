import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface V4ChipProps {
  children: ReactNode;
  active?: boolean;
  count?: number | string;
  onClick?: () => void;
  className?: string;
  type?: "button" | "span";
}

/** Filter / lane pill — Hive Control V4. */
export function V4Chip({ children, active, count, onClick, className, type = "button" }: V4ChipProps) {
  const cls = cn("v4-chip", active && "v4-chip--active", className);
  const content = (
    <>
      {children}
      {count !== undefined ? <span className="v4-chip-count">{count}</span> : null}
    </>
  );
  if (type === "span" || !onClick) {
    return <span className={cls}>{content}</span>;
  }
  return (
    <button type="button" className={cls} onClick={onClick}>
      {content}
    </button>
  );
}
