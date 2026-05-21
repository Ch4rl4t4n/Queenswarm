import { Loader2Icon } from "lucide-react";

import { V4Card } from "@/components/ui/v4";

/** Lightweight placeholder while the queen dashboard shell hydrates. */
export function ColonyConsoleSkeleton() {
  return (
    <div className="space-y-5 pb-8">
      <div className="space-y-3">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-white/10" />
        <div className="h-4 w-72 max-w-full animate-pulse rounded bg-white/5" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <V4Card key={i} className="h-28 animate-pulse bg-black/35">
            <span className="sr-only">Loading stat</span>
          </V4Card>
        ))}
      </div>
      <V4Card className="flex min-h-[280px] items-center justify-center">
        <Loader2Icon className="h-7 w-7 animate-spin text-pollen" aria-hidden />
      </V4Card>
    </div>
  );
}

/** Compact skeleton for lazy dashboard widgets. */
export function DashboardSectionSkeleton({ className }: { className?: string }) {
  return (
    <V4Card className={`min-h-[120px] animate-pulse bg-black/30 ${className ?? ""}`}>
      <span className="sr-only">Loading section</span>
    </V4Card>
  );
}
