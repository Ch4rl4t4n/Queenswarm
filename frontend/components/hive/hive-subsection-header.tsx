import type { ReactNode } from "react";

import { InlineSectionHintKey } from "@/components/hive/inline-section-hint";
import type { SectionHintKey } from "@/lib/section-hints";
import { cn } from "@/lib/utils";

type SubsectionTone = "default" | "cyan" | "pollen" | "magenta";

interface HiveSubsectionHeaderProps {
  title: string;
  description: ReactNode;
  hintKey?: SectionHintKey;
  hint?: ReactNode;
  tone?: SubsectionTone;
  className?: string;
}

const TITLE_TONE: Record<SubsectionTone, string> = {
  default: "text-(--qs-muted)",
  cyan: "text-cyan",
  pollen: "text-pollen",
  magenta: "text-[#FF00AA]",
};

/**
 * Nested block inside a card: title → description + inline hint.
 * Use for Command lane sub-tools, ICM blocks, etc.
 */
export function HiveSubsectionHeader({
  title,
  description,
  hintKey,
  hint,
  tone = "default",
  className,
}: HiveSubsectionHeaderProps) {
  const hintNode = hint ?? (hintKey ? <InlineSectionHintKey hintKey={hintKey} /> : null);

  return (
    <div className={cn(className)}>
      <p className={cn("text-xs font-semibold uppercase tracking-wider", TITLE_TONE[tone])}>{title}</p>
      <p className="mt-1 text-xs text-(--qs-muted)">
        {description}
        {hintNode}
      </p>
    </div>
  );
}
