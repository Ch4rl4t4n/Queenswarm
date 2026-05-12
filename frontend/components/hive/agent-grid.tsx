import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface AgentGridProps {
  children: ReactNode;
  className?: string;
}

/** Staggered honeycomb rhythm — even columns drop on large screens. */
export function AgentGrid({ children, className }: AgentGridProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-3 gap-x-2 gap-y-8 md:gap-x-3 lg:grid-cols-4 lg:gap-x-5 lg:gap-y-12 [&>*:nth-child(even)]:lg:translate-y-10",
        className,
      )}
    >
      {children}
    </div>
  );
}
