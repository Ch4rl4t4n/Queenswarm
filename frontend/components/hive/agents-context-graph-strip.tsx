"use client";

import type { JSX } from "react";

import Link from "next/link";
import { Loader2Icon, RefreshCwIcon } from "lucide-react";
import { useMemo } from "react";
import useSWR from "swr";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";
import { COCKPIT_POLL_HIVE_MIND_GRAPH_MS } from "@/lib/cockpit-poll-profile";
import {
  goalSearchQuery,
  matchGraphNodeFocusIds,
  probeGoalTokens,
} from "@/lib/hive-graph-focus";
import { useSwrVisiblePollOptions } from "@/lib/hooks/use-swr-refresh-interval";
import { cn } from "@/lib/utils";

interface HiveGraphNode {
  id: string;
  label: string;
  graph_kind?: string;
}

interface HiveGraphEdge {
  source: string;
  target: string;
  kind?: string;
}

interface HiveGraphPayload {
  nodes: HiveGraphNode[];
  edges: HiveGraphEdge[];
  degraded?: boolean;
  fallback_backend?: string;
}

interface HiveSearchPayload {
  items: {
    id?: string;
    document?: string | null;
    metadata?: Record<string, unknown>;
  }[];
}

interface LayoutNode extends HiveGraphNode {
  x: number;
  y: number;
}

interface AgentsContextGraphStripProps {
  /** When set, semantic search + token match highlights related nodes. */
  focusGoal?: string | null;
  focusSessionLabel?: string | null;
}

function layoutNodes(nodes: HiveGraphNode[], width: number, height: number): LayoutNode[] {
  if (nodes.length === 0) {
    return [];
  }
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.36;
  return nodes.map((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
    return {
      ...node,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  });
}

function MiniHiveGraphSvg({
  nodes,
  edges,
  focusedIds,
}: {
  nodes: LayoutNode[];
  edges: HiveGraphEdge[];
  focusedIds: Set<string>;
}): JSX.Element {
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  return (
    <svg viewBox="0 0 360 140" className="h-[140px] w-full" aria-hidden>
      {edges.map((edge, index) => {
        const source = nodeById.get(edge.source);
        const target = nodeById.get(edge.target);
        if (!source || !target) {
          return null;
        }
        const focused = focusedIds.has(edge.source) || focusedIds.has(edge.target);
        return (
          <line
            key={`${edge.source}-${edge.target}-${index}`}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke={focused ? "rgba(0,255,255,0.65)" : "rgba(0,255,255,0.25)"}
            strokeWidth={focused ? 1.6 : 1}
          />
        );
      })}
      {nodes.map((node) => {
        const focused = focusedIds.has(node.id);
        return (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={focused ? 12 : 10}
              fill={focused ? "rgba(0,255,255,0.25)" : "rgba(255,184,0,0.15)"}
              stroke={focused ? "#00FFFF" : "#FFB800"}
              strokeWidth={focused ? 2 : 1.2}
            />
            <text x={node.x} y={node.y + 3} textAnchor="middle" fontSize="7" fill="#E5E7EB">
              {(node.label || node.id).slice(0, 3).toUpperCase()}
            </text>
          </g>
        );
      })}
      <circle cx="180" cy="70" r="12" fill="rgba(255,184,0,0.35)" stroke="#FFB800" strokeWidth="1.5" />
      <text x="180" y="74" textAnchor="middle" fontSize="8" fill="#050510" fontWeight="700">
        Q
      </text>
    </svg>
  );
}

/** Compact live Neo4j / vector fallback snapshot for the Agents control plane. */
export function AgentsContextGraphStrip({ focusGoal, focusSessionLabel }: AgentsContextGraphStripProps): JSX.Element {
  const pollOptions = useSwrVisiblePollOptions(COCKPIT_POLL_HIVE_MIND_GRAPH_MS);
  const searchQuery = focusGoal?.trim() ? goalSearchQuery(focusGoal) : "";

  const { data, error, isLoading, mutate } = useSWR<HiveGraphPayload>(
    "hive/agents-context-graph",
    () => hiveGet<HiveGraphPayload>("hive-mind/graph?limit_nodes=24"),
    pollOptions,
  );

  const { data: searchData } = useSWR<HiveSearchPayload>(
    searchQuery.length >= 4 ? `hive/agents-graph-focus:${searchQuery}` : null,
    () => hiveGet<HiveSearchPayload>(`hive-mind/search?q=${encodeURIComponent(searchQuery)}&limit=8`),
    { revalidateOnFocus: false },
  );

  const graphNodes = (data?.nodes ?? []).slice(0, 24);
  const nodes = layoutNodes(graphNodes, 360, 140);
  const goalTokens = useMemo(() => (focusGoal ? probeGoalTokens(focusGoal) : []), [focusGoal]);
  const focusedIds = useMemo(
    () => matchGraphNodeFocusIds(graphNodes, searchData?.items ?? [], goalTokens),
    [graphNodes, searchData?.items, goalTokens],
  );

  return (
    <V4Card className="relative p-4 md:p-5">
      <button
        type="button"
        aria-label="Refresh context graph"
        className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-[12px] border border-(--qs-border) text-(--qs-text-3) hover:border-(--qs-border-2) hover:text-pollen touch-manipulation md:right-5 md:top-5"
        disabled={isLoading}
        onClick={() => void mutate()}
      >
        <RefreshCwIcon className={cn("h-5 w-5", isLoading && "animate-spin")} aria-hidden />
      </button>

      <div className="pr-12">
        <V4CardHeader
          as="h2"
          kicker="Shared memory"
          title="Context graph"
          description="Neo4j constellation linked to supervisor sessions — refreshes while tab is visible."
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Link href="/knowledge" className="qs-btn qs-btn--primary qs-btn--sm">
          Open vault
        </Link>
        {focusSessionLabel ? <V4Badge tone="info">focus · {focusSessionLabel}</V4Badge> : null}
        {focusedIds.size > 0 ? <V4Badge tone="ok">{focusedIds.size} matched</V4Badge> : null}
        {data?.degraded ? <V4Badge tone="warn">vector fallback</V4Badge> : null}
        <span className="text-xs tabular-nums text-(--qs-text-3)">
          {data?.nodes?.length ?? 0} nodes · {data?.edges?.length ?? 0} edges
        </span>
      </div>

      {focusGoal ? (
        <p className="mt-2 line-clamp-2 text-[11px] text-(--qs-text-3)">
          Goal probe: <span className="text-cyan">{searchQuery || focusGoal.slice(0, 120)}</span>
        </p>
      ) : null}

      {isLoading && !data ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin text-pollen" aria-hidden />
          Loading graph snapshot…
        </div>
      ) : error ? (
        <p className="mt-4 text-sm text-(--qs-text-3)">Context graph unavailable — Hive Mind may be offline.</p>
      ) : nodes.length === 0 ? (
        <p className="mt-4 text-sm text-(--qs-text-3)">
          No graph nodes yet — supervisor writes populate vector + graph lanes automatically.
        </p>
      ) : (
        <div className="mt-3 rounded-xl border border-cyan/15 bg-black/25 p-2">
          <MiniHiveGraphSvg nodes={nodes} edges={data?.edges ?? []} focusedIds={focusedIds} />
        </div>
      )}
    </V4Card>
  );
}
