import { Loader2 } from "lucide-react";

import { V4Card } from "@/components/ui/v4";

interface HivePanelSectionSkeletonProps {
  label?: string;
  minHeightClass?: string;
}

/** Lazy-loaded panel placeholder inside HivePageShell content (Phase 8.2). */
export function HivePanelSectionSkeleton({
  label = "Loading panel…",
  minHeightClass = "min-h-[16rem]",
}: HivePanelSectionSkeletonProps) {
  return (
    <V4Card>
      <div
        className={`flex ${minHeightClass} items-center justify-center gap-2 text-sm text-(--qs-muted)`}
        role="status"
        aria-label={label}
      >
        <Loader2 className="size-4 animate-spin" aria-hidden />
        {label}
      </div>
    </V4Card>
  );
}
