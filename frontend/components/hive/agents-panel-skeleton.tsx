import type { JSX } from "react";

/** Pulse placeholders for Agents hub panels while SWR loads. */
export function AgentsPanelSkeleton({ rows = 3 }: { rows?: number }): JSX.Element {
  return (
    <div className="flex flex-col gap-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="h-16 animate-pulse rounded-xl border border-(--qs-border) bg-black/30"
        />
      ))}
    </div>
  );
}
