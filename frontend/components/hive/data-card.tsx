import { V4Stat, type V4StatIcon, type V4StatIconTone } from "@/components/ui/v4/v4-stat";
import { cn } from "@/lib/utils";

interface DataCardProps {
  label: string;
  value: string;
  icon: V4StatIcon;
  /** Whole-number or decimal trend; omit when unknown (no fake deltas). */
  trendPercent?: number | null;
  hint?: string;
  className?: string;
  iconTone?: V4StatIconTone;
}

function trendMeta(delta: number): { dir: "up" | "down"; text: string } | null {
  if (delta > 0) {
    return { dir: "up", text: `+${delta}% vs prior window` };
  }
  if (delta < 0) {
    return { dir: "down", text: `${delta}% vs prior window` };
  }
  return { dir: "up", text: "0% vs prior window" };
}

/** Metric tile with optional verified trend — Hive Control V4. */
export function DataCard({ label, value, icon, trendPercent, hint, className, iconTone = "default" }: DataCardProps) {
  const showTrend = typeof trendPercent === "number" && !Number.isNaN(trendPercent);
  const trend =
    showTrend && trendPercent !== null && trendPercent !== undefined
      ? trendMeta(Math.round(trendPercent))
      : undefined;

  return (
    <V4Stat
      label={label}
      value={value}
      icon={icon}
      iconTone={iconTone}
      foot={hint}
      trend={trend ?? undefined}
      className={cn(className)}
    />
  );
}
