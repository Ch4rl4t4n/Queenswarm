import type { LucideIcon } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

import { cn } from "@/lib/utils";

export type V4StatIconTone = "default" | "purple" | "cyan" | "green";

/** Lucide icons or Hive Control V4 custom SVG icons. */
export type V4StatIcon = LucideIcon | ComponentType<{ className?: string; size?: number }>;

interface V4StatProps {
  label: string;
  value: ReactNode;
  icon?: V4StatIcon;
  iconTone?: V4StatIconTone;
  foot?: string;
  trend?: { dir: "up" | "down"; text: string };
  valueVariant?: "gold" | "text";
  className?: string;
}

const iconToneClass: Record<V4StatIconTone, string> = {
  default: "",
  purple: "v4-stat-icon--purple",
  cyan: "v4-stat-icon--cyan",
  green: "v4-stat-icon--green",
};

/** KPI tile — Hive Control V4 (matches design-reference Stat). */
export function V4Stat({
  label,
  value,
  icon: Icon,
  iconTone = "default",
  foot,
  trend,
  valueVariant = "gold",
  className,
}: V4StatProps) {
  return (
    <article className={cn("v4-stat", className)}>
      <div className="v4-stat-head">
        <span className="v4-stat-label">{label}</span>
        {Icon ? (
          <span className={cn("v4-stat-icon", iconToneClass[iconTone])}>
            <Icon className="h-4 w-4" size={16} />
          </span>
        ) : null}
      </div>
      <div className={cn("v4-stat-value", valueVariant === "text" && "v4-stat-value--text")}>{value}</div>
      {trend ? (
        <div className={cn("v4-stat-trend", trend.dir === "down" && "v4-stat-trend--down")}>{trend.text}</div>
      ) : null}
      {foot ? <div className="v4-stat-foot">{foot}</div> : null}
    </article>
  );
}
