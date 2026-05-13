import type { LucideIcon } from "lucide-react";
import { ArrowDownRightIcon, ArrowUpRightIcon, MinusIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface DataCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  /** Whole-number or decimal trend; omit when unknown (no fake deltas). */
  trendPercent?: number | null;
  hint?: string;
  className?: string;
}

function trendMeta(delta: number): { Icon: typeof ArrowUpRightIcon; className: string; text: string } {
  if (delta > 0) {
    return {
      Icon: ArrowUpRightIcon,
      className: "text-success",
      text: `+${delta}%`,
    };
  }
  if (delta < 0) {
    return {
      Icon: ArrowDownRightIcon,
      className: "text-danger",
      text: `${delta}%`,
    };
  }
  return { Icon: MinusIcon, className: "text-cyan/70", text: "0%" };
}

/** Metric tile with optional verified trend (omit trend when API has no baseline). */
export function DataCard({ label, value, icon: Icon, trendPercent, hint, className }: DataCardProps) {
  const showTrend = typeof trendPercent === "number" && !Number.isNaN(trendPercent);
  const meta = showTrend ? trendMeta(Math.round(trendPercent)) : null;

  return (
    <article
      className={cn(
        "relative overflow-hidden rounded-2xl border border-cyan/18 bg-gradient-to-br from-[#0c0e22] via-[#070814] to-[#050510] p-5 shadow-[0_18px_44px_rgba(0,0,0,0.55)]",
        className,
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(125deg,rgba(0,255,255,0.07),transparent_55%)]" />
      <div className="relative flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="font-[family-name:var(--font-poppins)] text-xs font-medium uppercase tracking-[0.14em] text-cyan/75">
            {label}
          </p>
          <p className="font-[family-name:var(--font-poppins)] text-3xl font-semibold tracking-tight text-pollen shadow-[0_0_28px_rgba(255,184,0,0.38)]">
            {value}
          </p>
          {hint ? (
            <p className="font-[family-name:var(--font-poppins)] text-[11px] text-muted-foreground">{hint}</p>
          ) : null}
        </div>
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-data/25 bg-black/40 text-data shadow-[0_0_22px_rgba(0,255,255,0.22)]"
          aria-hidden
        >
          <Icon className="h-6 w-6" />
        </div>
      </div>
      {meta ? (
        <div className={cn("relative mt-4 flex items-center gap-1 font-[family-name:var(--font-poppins)] text-xs", meta.className)}>
          <meta.Icon className="h-3.5 w-3.5" aria-hidden />
          <span>{meta.text}</span>
          <span className="sr-only"> versus prior window</span>
        </div>
      ) : null}
    </article>
  );
}
