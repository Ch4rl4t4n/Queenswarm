"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef } from "react";

import { AgentListRow } from "@/components/hive/agents-list-row";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import type { AgentRow } from "@/lib/hive-types";

interface AgentsVirtualListProps {
  readonly agents: AgentRow[];
  readonly onAgentActivate: (agent: AgentRow) => void;
}

/** Windowed list for large rosters — only mounts visible rows. */
export function AgentsVirtualList({ agents, onAgentActivate }: AgentsVirtualListProps): JSX.Element {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowStride = COCKPIT_PERF.listVirtualRowPx + COCKPIT_PERF.listVirtualRowGapPx;

  const virtualizer = useVirtualizer({
    count: agents.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowStride,
    overscan: COCKPIT_PERF.listVirtualOverscan,
  });

  return (
    <div
      ref={parentRef}
      className="mt-8 max-h-[min(70vh,720px)] overflow-y-auto overscroll-contain pr-1"
      role="list"
      aria-label={`${agents.length} agents`}
    >
      <div
        className="relative w-full"
        style={{ height: `${virtualizer.getTotalSize()}px` }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const agent = agents[virtualRow.index];
          if (!agent) {
            return null;
          }
          return (
            <div
              key={agent.id}
              role="listitem"
              className="absolute left-0 top-0 w-full pb-3"
              style={{ transform: `translateY(${virtualRow.start}px)` }}
            >
              <AgentListRow agent={agent} onActivate={onAgentActivate} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
