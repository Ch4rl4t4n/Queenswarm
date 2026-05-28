"use client";

import Link from "next/link";
import { LayoutGrid, List, Play, Plus } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { AgentListRow } from "@/components/hive/agents-list-row";
import { AgentsVirtualList } from "@/components/hive/agents-virtual-list";
import { HexAgentCard } from "@/components/hive/hex-agent-card";
import { V4Card, V4CardHeader, V4Chip } from "@/components/ui/v4";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { laneTabLabel, shouldVirtualizeAgentList, workerSwarmPillBucket } from "@/lib/agents-list-presenters";
import type { AgentsSwarmFilter } from "@/lib/agent-hive-lane";
import { isQueenAgent } from "@/lib/agent-hive-lane";
import { MEDIA_QUERIES } from "@/lib/breakpoints";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { useCenterActiveInScrollRow } from "@/lib/hooks/use-center-active-in-scroll-row";
import type { AgentRow } from "@/lib/hive-types";

export type { AgentsSwarmFilter, AgentHiveLane } from "@/lib/agent-hive-lane";
export { laneTheme, roleDisplayName } from "@/lib/agents-list-presenters";

type ViewMode = "grid" | "list";

function filledHiveId(value: unknown): boolean {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

function hasSubSwarmId(agent: AgentRow): boolean {
  return filledHiveId(agent.sub_swarm_id);
}

interface AgentsLiveSectionProps {
  agents: AgentRow[];
  onAgentActivate: (agent: AgentRow) => void;
  onRebalanceHive: () => Promise<void>;
  rebalanceBusy: boolean;
  /** Primary CTA for spawning — dashboard defaults to cockpit anchor. */
  spawnAgentHref?: string;
  title?: string;
  description?: ReactNode;
  /** Full roster pages — windowed list instead of cap + "Show more". */
  virtualizeList?: boolean;
}

export function AgentsLiveSection({
  agents: rawAgents,
  onAgentActivate,
  onRebalanceHive,
  rebalanceBusy,
  spawnAgentHref,
  title = "Agents",
  description,
  virtualizeList = false,
}: AgentsLiveSectionProps) {
  const agents = useMemo(() => (Array.isArray(rawAgents) ? rawAgents : []), [rawAgents]);
  const [swarmFilter, setSwarmFilter] = useState<AgentsSwarmFilter>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [listExpanded, setListExpanded] = useState(false);
  const [gridExpanded, setGridExpanded] = useState(false);
  const filterScrollRef = useCenterActiveInScrollRow(swarmFilter);
  const spawnHref = spawnAgentHref ?? "/#hive-create";

  useEffect(() => {
    if (window.matchMedia(MEDIA_QUERIES.mobile).matches) {
      setViewMode("list");
    }
  }, []);

  const counts = useMemo(() => {
    let scout = 0;
    let evalc = 0;
    let sim = 0;
    let action = 0;
    let unassigned = 0;
    for (const a of agents) {
      if (isQueenAgent(a)) {
        continue;
      }
      const lane = workerSwarmPillBucket(a);
      if (lane === "scout") {
        scout += 1;
      } else if (lane === "eval") {
        evalc += 1;
      } else if (lane === "sim") {
        sim += 1;
      } else if (lane === "action") {
        action += 1;
      } else if (lane === "unassigned") {
        unassigned += 1;
      }
    }
    return { all: agents.length, unassigned, scout, eval: evalc, sim, action };
  }, [agents]);

  const roleTypeCount = useMemo(() => new Set(agents.map((a) => a.role.toLowerCase())).size, [agents]);

  const swarmCountDistinct = useMemo(() => {
    const ids = new Set<string>();
    for (const a of agents) {
      if (isQueenAgent(a)) {
        continue;
      }
      if (!hasSubSwarmId(a)) {
        continue;
      }
      ids.add(String(a.sub_swarm_id));
    }
    return ids.size;
  }, [agents]);

  const assignedWorkerCount = useMemo(
    () =>
      agents.filter((a) => !isQueenAgent(a) && workerSwarmPillBucket(a) !== "unassigned").length,
    [agents],
  );

  const filtered = useMemo(() => {
    if (swarmFilter === "all") {
      return agents;
    }
    return agents.filter((a) => !isQueenAgent(a) && workerSwarmPillBucket(a) === swarmFilter);
  }, [agents, swarmFilter]);

  const useVirtualList = shouldVirtualizeAgentList(filtered.length, virtualizeList);
  const listRenderCap = COCKPIT_PERF.listInitialRender;
  const gridRenderCap = COCKPIT_PERF.gridInitialRender;
  const listOverflow = !useVirtualList && filtered.length > listRenderCap;
  const gridOverflow = virtualizeList && filtered.length > gridRenderCap;
  const visibleList =
    viewMode === "list" && !useVirtualList && !listExpanded ? filtered.slice(0, listRenderCap) : filtered;
  const visibleGrid =
    viewMode === "grid" && gridOverflow && !gridExpanded ? filtered.slice(0, gridRenderCap) : filtered;

  const pills: { key: AgentsSwarmFilter; count: number }[] = [
    { key: "all", count: counts.all },
    { key: "unassigned", count: counts.unassigned },
    { key: "scout", count: counts.scout },
    { key: "eval", count: counts.eval },
    { key: "sim", count: counts.sim },
    { key: "action", count: counts.action },
  ];

  return (
    <V4Card id="hive-live-swarm" className="scroll-mt-24 v4-card-interactive">
      <V4CardHeader
        title={title}
        description={
          description ?? (
            <>
              {counts.all} bees · {assignedWorkerCount} assigned to swarms · {counts.unassigned} unassigned ·{" "}
              {swarmCountDistinct} swarms with at least one bee · {roleTypeCount} role types
            </>
          )
        }
        hint={sectionHintNode("agentsRoster")}
        actions={
          <div className="flex w-full items-center justify-between gap-3">
            <Link href={spawnHref} className="qs-btn qs-btn--ghost qs-btn--sm shrink-0 gap-2">
              <Plus className="h-4 w-4 shrink-0" aria-hidden />
              Add agent
            </Link>
            <button
              type="button"
              disabled={rebalanceBusy}
              onClick={() => void onRebalanceHive()}
              className="qs-btn qs-btn--primary qs-btn--sm shrink-0 gap-2 disabled:opacity-40"
            >
              <Play className="h-4 w-4 shrink-0" aria-hidden />
              {rebalanceBusy ? "Working…" : "Balance hive"}
            </button>
          </div>
        }
      />

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div ref={filterScrollRef} className="v4-chip-scroll md:flex-wrap md:overflow-visible">
          {pills.map(({ key, count }) => {
            const active = swarmFilter === key;
            const label =
              key === "all" ? "All" : laneTabLabel(key as Exclude<AgentsSwarmFilter, "all">);
            return (
              <V4Chip key={key} active={active} onClick={() => setSwarmFilter(key)}>
                {label}
                <span className="v4-chip-count">· {count}</span>
              </V4Chip>
            );
          })}
        </div>
        <div role="group" aria-label="View" className="flex flex-wrap gap-2">
          <V4Chip active={viewMode === "grid"} onClick={() => setViewMode("grid")}>
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden />
            Grid
          </V4Chip>
          <V4Chip active={viewMode === "list"} onClick={() => setViewMode("list")}>
            <List className="h-3.5 w-3.5" aria-hidden />
            List
          </V4Chip>
        </div>
      </div>

      {viewMode === "grid" ? (
        <div className="v4-agent-grid mx-auto max-w-[1200px]">
          {visibleGrid.map((agent) => (
            <HexAgentCard
              key={agent.id}
              agent={agent}
              showPerformance
              onClick={() => onAgentActivate(agent)}
            />
          ))}
        </div>
      ) : useVirtualList ? (
        <AgentsVirtualList agents={filtered} onAgentActivate={onAgentActivate} />
      ) : (
        <ul className="mt-8 space-y-3">
          {visibleList.map((agent) => (
            <li key={agent.id}>
              <AgentListRow agent={agent} onActivate={onAgentActivate} />
            </li>
          ))}
        </ul>
      )}

      {viewMode === "grid" && gridOverflow && !gridExpanded ? (
        <button
          type="button"
          className="mt-4 w-full rounded-xl border border-(--qs-border) bg-black/30 py-2 text-sm text-(--qs-text-2) hover:border-pollen/35 hover:text-pollen"
          onClick={() => setGridExpanded(true)}
        >
          Show {filtered.length - gridRenderCap} more hex cards
        </button>
      ) : null}

      {viewMode === "list" && listOverflow && !listExpanded ? (
        <button
          type="button"
          className="mt-4 w-full rounded-xl border border-(--qs-border) bg-black/30 py-2 text-sm text-(--qs-text-2) hover:border-pollen/35 hover:text-pollen"
          onClick={() => setListExpanded(true)}
        >
          Show {filtered.length - listRenderCap} more bees
        </button>
      ) : null}

      {filtered.length === 0 ? (
        <p className="mt-10 text-center text-sm text-(--qs-text-3)">No agents match this filter.</p>
      ) : null}
    </V4Card>
  );
}
