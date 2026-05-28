import { V4PageCanvas } from "@/components/ui/v4";
import { cn } from "@/lib/utils";

interface HivePageShellSkeletonProps {
  /** Match HivePageShell subnav row placeholder. */
  withSubnav?: boolean;
  className?: string;
}

/**
 * Route-level skeleton aligned with HivePageShell layout (Phase 8 performance pass).
 */
export function HivePageShellSkeleton({ withSubnav = false, className }: HivePageShellSkeletonProps) {
  return (
    <V4PageCanvas
      data-testid="hive-page-shell-skeleton"
      role="status"
      aria-label="Loading page"
      aria-busy="true"
      className={cn("hive-page-shell-skeleton", className)}
    >
      <div className="qs-page-header mb-4 space-y-3 lg:mb-5">
        <div className="flex items-start justify-between gap-3">
          <div className="h-9 w-48 max-w-[70%] animate-pulse rounded-lg bg-white/6" />
          <div className="hidden h-8 w-24 animate-pulse rounded-full bg-white/5 sm:block" />
        </div>
        <div className="h-4 w-full max-w-xl animate-pulse rounded bg-white/4" />
      </div>

      {withSubnav ? (
        <div className="hive-page-shell-subnav mb-4 flex flex-wrap gap-2">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={`subnav-skel-${index}`} className="h-9 w-[5.5rem] animate-pulse rounded-full bg-white/5" />
          ))}
        </div>
      ) : null}

      <div className="hive-page-shell-content space-y-4">
        <div className="h-36 animate-pulse rounded-2xl border border-[color:var(--qs-border)] bg-white/[0.03]" />
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }, (_, index) => (
            <div
              key={`card-skel-${index}`}
              className="h-28 animate-pulse rounded-2xl border border-[color:var(--qs-border)] bg-white/[0.03]"
            />
          ))}
        </div>
      </div>
    </V4PageCanvas>
  );
}
