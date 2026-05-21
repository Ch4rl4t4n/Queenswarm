"use client";

import { useState } from "react";
import nextDynamic from "next/dynamic";
import Link from "next/link";
import { toast } from "sonner";

import { AgentsLiveSection } from "@/components/hive/agents-live-section";
import { DashboardSectionSkeleton } from "@/components/hive/colony-console-skeleton";
import { useDashboardSection, useDashboardLayout } from "@/components/hive/dashboard-layout-provider";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";
import {
  V4BarRow,
  V4Card,
  V4CardHeader,
  V4IconAgents,
  V4IconBolt,
  V4IconCoin,
  V4IconCpu,
  V4IconPollen,
  V4IconQueue,
  V4QueenMission,
  V4PageCanvas,
  V4SearchInput,
  V4Stat,
  V4StatGrid,
} from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";
import { dashboardPageDensityClass } from "@/lib/section-hub";
import { cn } from "@/lib/utils";

const PaperTradingPanel = nextDynamic(
  () => import("@/components/hive/paper-trading-panel").then((mod) => ({ default: mod.PaperTradingPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[140px]" /> },
);

const SubSwarmsSection = nextDynamic(
  () => import("@/components/hive/swarm-board-section").then((mod) => ({ default: mod.SubSwarmsSection })),
  { loading: () => <DashboardSectionSkeleton /> },
);

const WaggleFeedCard = nextDynamic(
  () => import("@/components/hive/swarm-board-section").then((mod) => ({ default: mod.WaggleFeedCard })),
  { loading: () => <DashboardSectionSkeleton /> },
);

const WorkflowsSection = nextDynamic(
  () => import("@/components/hive/workflows-section").then((mod) => ({ default: mod.WorkflowsSection })),
  { loading: () => <DashboardSectionSkeleton className="h-48" /> },
);

const TaskQueueSection = nextDynamic(
  () => import("@/components/hive/task-queue-section").then((mod) => ({ default: mod.TaskQueueSection })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[200px]" /> },
);

const RapidLoopWidget = nextDynamic(
  () => import("@/components/hive/rapid-loop-widget").then((mod) => ({ default: mod.RapidLoopWidget })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[160px]" /> },
);

const DreamingSummaryCard = nextDynamic(
  () => import("@/components/hive/dreaming-summary-card").then((mod) => ({ default: mod.DreamingSummaryCard })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[140px]" /> },
);

const PatternExplorerSection = nextDynamic(
  () => import("@/components/hive/pattern-explorer-card").then((mod) => ({ default: mod.PatternExplorerSection })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[140px]" /> },
);

const TimeSavedPanel = nextDynamic(
  () => import("@/components/hive/time-saved-panel").then((mod) => ({ default: mod.TimeSavedPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[160px]" /> },
);

const SwarmBuilderEntryCard = nextDynamic(
  () => import("@/components/hive/swarm-builder-entry-card").then((mod) => ({ default: mod.SwarmBuilderEntryCard })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[88px]" /> },
);

const LeadMagnetPanel = nextDynamic(
  () => import("@/components/hive/lead-magnet-panel").then((mod) => ({ default: mod.LeadMagnetPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[160px]" /> },
);

const BeeBadgesPanel = nextDynamic(
  () => import("@/components/hive/bee-badges-panel").then((mod) => ({ default: mod.BeeBadgesPanel })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[160px]" /> },
);

const V4BallroomParticipants = nextDynamic(
  () => import("@/components/ui/v4/v4-ballroom-participants").then((mod) => ({ default: mod.V4BallroomParticipants })),
  { loading: () => <DashboardSectionSkeleton className="min-h-[88px]" /> },
);

function formatPollen(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(Math.round(n * 10) / 10);
}

function formatUsd(n: number | null): string {
  if (n === null || Number.isNaN(n)) return "—";
  if (n < 0.01 && n > 0) return `<$0.01`;
  return `$${n.toFixed(2)}`;
}

function statusDotClass(status: string): string {
  const u = status.toUpperCase();
  if (u.includes("RUN")) return "bg-(--qs-cyan) shadow-[0_0_8px_rgba(111,214,255,0.8)]";
  if (u.includes("PEND") || u.includes("QUEUE")) return "bg-pollen shadow-[0_0_6px_rgb(255_184_0/0.45)]";
  if (u.includes("COMP")) return "bg-success";
  if (u === "IDLE") return "bg-success";
  if (u === "PAUSED") return "bg-alert";
  if (u === "OFFLINE" || u === "ERROR" || u.includes("FAIL")) return "bg-danger";
  return "bg-zinc-500";
}

function taskStatusBrief(statusRaw: string): string {
  return statusRaw.replaceAll("_", " ");
}

interface QueenDashboardChromeProps {
  agents: AgentRow[];
  summary: DashboardSummary | null;
  costWindowUsd: number | null;
  filterQuery: string;
  onFilterChange: (q: string) => void;
  onHoneycombAgent: (agent: AgentRow) => void;
  onAgentsReload: () => void | Promise<void>;
  swarmLabelCount: number;
  systemStatus?: SystemStatusPayload | null;
  recentTasks?: TaskRow[];
  telemetryLoading?: boolean;
  missionBrief: string;
  onMissionBriefChange: (value: string) => void;
  onRunMission: () => void;
  missionBusy: boolean;
  missionErr: string | null;
}

export function QueenDashboardChrome({
  agents,
  summary,
  costWindowUsd,
  filterQuery,
  onFilterChange,
  onHoneycombAgent,
  onAgentsReload,
  swarmLabelCount,
  systemStatus = null,
  recentTasks = [],
  telemetryLoading = false,
  missionBrief,
  onMissionBriefChange,
  onRunMission,
  missionBusy,
  missionErr,
}: QueenDashboardChromeProps) {
  const showSearch = useDashboardSection("search");
  const showKpiStats = useDashboardSection("kpiStats");
  const showPollenCosts = useDashboardSection("pollenCosts");
  const showBallroom = useDashboardSection("ballroomParticipants");
  const showAgents = useDashboardSection("agents");
  const showQueenMission = useDashboardSection("queenMission");
  const showSubSwarms = useDashboardSection("subSwarms");
  const showWaggle = useDashboardSection("waggleFeed");
  const showWorkflows = useDashboardSection("workflows");
  const showTaskQueue = useDashboardSection("taskQueue");
  const showPerformanceTier = useDashboardSection("performanceTier");
  const showRecentTasks = useDashboardSection("recentTasks");
  const showSwarmBuilderEntry = useDashboardSection("swarmBuilderEntry");
  const showRapidLoop = useDashboardSection("rapidLoop");
  const showDreamingSummary = useDashboardSection("dreamingSummary");
  const showPatternExplorer = useDashboardSection("patternExplorer");
  const showTimeSaved = useDashboardSection("timeSaved");
  const showLeadMagnets = useDashboardSection("leadMagnets");
  const showBeeBadges = useDashboardSection("beeBadges");
  const { density } = useDashboardLayout();

  const [rebalanceBusy, setRebalanceBusy] = useState(false);
  const pollenTotal = agents.reduce((s, a) => s + (a.pollen_points ?? 0), 0);
  const pendingFallback = summary?.tasks.pending ?? 0;
  const totalAgentsListed = agents.length;
  const totalAgentsGauge = Math.max(totalAgentsListed, systemStatus?.agents_total ?? 0);
  const activeAgents = agents.filter((a) => ["RUNNING", "IDLE", "BUSY"].includes(String(a.status).toUpperCase())).length;
  const idleAgents = Math.max(0, totalAgentsListed - activeAgents);

  const runningTasks = systemStatus?.tasks_running ?? 0;
  const queuedTasks = systemStatus?.tasks_pending ?? pendingFallback;
  const llmOk = Boolean(systemStatus?.llm_grok || systemStatus?.llm_anthropic);
  const showKpiPulse = telemetryLoading && !systemStatus;

  const tierBars = (() => {
    const m = summary?.agents.by_hive_tier ?? {};
    const tot = Math.max(1, Object.values(m).reduce((a, b) => a + b, 0));
    const rows = [
      { key: "orchestrator", label: "Queen" },
      { key: "manager", label: "Managers" },
      { key: "worker", label: "Workers" },
      { key: "unknown", label: "Unassigned" },
    ];
    return rows.map((r) => ({
      ...r,
      pct: Math.round(((m[r.key] ?? 0) / tot) * 100),
      count: m[r.key] ?? 0,
    }));
  })();

  async function rebalanceHive(): Promise<void> {
    setRebalanceBusy(true);
    try {
      const res = await hivePostJson<{ woken?: number; message?: string }>("agents/wake-all", {});
      toast.success(res.message ?? "Paused bees are back to idle.");
      await Promise.resolve(onAgentsReload());
    } catch (e) {
      const msg = e instanceof HiveApiError ? e.message : e instanceof Error ? e.message : "Rebalance failed";
      toast.error(msg);
    } finally {
      setRebalanceBusy(false);
    }
  }

  const showSwarmSignals = showWaggle || showWorkflows;
  const showInsights = showPerformanceTier || showRecentTasks;
  const showLearningInsights = showRapidLoop || showDreamingSummary || showPatternExplorer;

  return (
    <V4PageCanvas className={dashboardPageDensityClass(density)}>
      <HivePageHeader
        title="Dashboard"
        subtitle={`${totalAgentsGauge} agents in the network · ${swarmLabelCount} swarm nodes · hive sync every 5 min`}
        status={
          <span className="v4-status-pill inline-flex">
            <span className="hive-pulse-dot shrink-0" aria-hidden />
            Hive open
          </span>
        }
      />

      <HubEcosystemStrip preset="dashboard" />

      {showSwarmBuilderEntry ? <SwarmBuilderEntryCard /> : null}

      {showLeadMagnets ? <LeadMagnetPanel compact /> : null}

      {showSearch ? (
        <V4SearchInput
          value={filterQuery}
          onChange={onFilterChange}
          placeholder="Search agents, tier, name, swarm…"
          aria-label="Filter agents"
          className="!mb-0"
        />
      ) : null}

      {showKpiStats ? (
        <V4StatGrid>
          {showKpiPulse ? (
            [0, 1, 2, 3].map((i) => (
              <div key={String(i)} className="v4-stat animate-pulse">
                <div className="mb-4 h-4 w-2/5 rounded bg-white/10" />
                <div className="h-9 w-1/2 rounded bg-white/10" />
                <div className="mt-3 h-3 w-3/5 rounded bg-white/5" />
              </div>
            ))
          ) : (
            <>
              <V4Stat label="Total agents" value={totalAgentsListed} icon={V4IconAgents} iconTone="purple" foot={`${activeAgents} active · ${idleAgents} idle`} />
              <V4Stat label="Running tasks" value={runningTasks} icon={V4IconBolt} foot="From system pulse" />
              <V4Stat label="Queued tasks" value={queuedTasks} icon={V4IconQueue} iconTone="cyan" foot="Pending lane" />
              <V4Stat
                label="LLM routing"
                valueVariant="text"
                value={
                  <>
                    <span className={cn("hive-pulse-dot shrink-0", !llmOk && "bg-danger! shadow-none!")} aria-hidden />
                    {llmOk ? "Routed" : "Degraded"}
                  </>
                }
                icon={V4IconCpu}
                iconTone="green"
                foot={`Grok ${systemStatus?.llm_grok ? "·" : "—"} · Claude ${systemStatus?.llm_anthropic ? "·" : "—"} · GPT —`}
              />
            </>
          )}
        </V4StatGrid>
      ) : null}

      <PaperTradingPanel />

      {showPollenCosts ? (
        <div className="v4-cols-2">
          <article className="v4-stat">
            <div className="v4-stat-head">
              <span className="v4-stat-label">Pollen · Roster activity</span>
              <span className="v4-stat-icon">
                <V4IconPollen className="h-4 w-4" size={16} />
              </span>
            </div>
            <div className="v4-stat-value">{formatPollen(pollenTotal)}</div>
            <div className="v4-stat-foot">Signals routed today · roster sum</div>
            <div className="v4-stat-bars" aria-hidden>
              {[40, 55, 32, 68, 90, 72, 85, 60, 78, 95, 82, 70].map((h, i) => (
                <div
                  key={i}
                  className="v4-stat-bar"
                  style={{ height: `${h}%`, opacity: 0.6 + i / 24 }}
                />
              ))}
            </div>
          </article>
          <V4Stat label="Costs · 30 days" value={formatUsd(costWindowUsd)} icon={V4IconCoin} foot="Sums routed LLM spend — tasks, Ballroom chat, workflows" />
        </div>
      ) : null}

      {showBallroom ? <V4BallroomParticipants agents={agents} /> : null}

      {showAgents && agents.length === 0 ? (
        <V4Card tight className="v4-card-interactive text-center text-sm text-(--qs-text-2)">
          No agents in the hive yet —{" "}
          <Link href="/agents/new" className="font-semibold text-pollen underline-offset-4 hover:underline">
            Spawn first agent
          </Link>
        </V4Card>
      ) : null}

      {showAgents ? (
        <AgentsLiveSection agents={agents} onAgentActivate={onHoneycombAgent} onRebalanceHive={rebalanceHive} rebalanceBusy={rebalanceBusy} />
      ) : null}

      {showSubSwarms ? <SubSwarmsSection /> : null}

      {showSwarmSignals ? (
        <div className={cn(showWaggle && showWorkflows ? "v4-cols-2 v4-cols-2--stack-mobile" : "grid grid-cols-1 gap-5")}>
          {showWaggle ? <WaggleFeedCard /> : null}
          {showWorkflows ? <WorkflowsSection /> : null}
        </div>
      ) : null}

      {showTaskQueue ? <TaskQueueSection /> : null}

      {showRapidLoop || showDreamingSummary ? (
        <div
          className={cn(
            showRapidLoop && showDreamingSummary
              ? "v4-cols-2 v4-cols-2--stack-mobile"
              : "grid grid-cols-1 gap-5",
          )}
        >
          {showRapidLoop ? <RapidLoopWidget /> : null}
          {showDreamingSummary ? <DreamingSummaryCard /> : null}
        </div>
      ) : null}

      {showPatternExplorer ? <PatternExplorerSection /> : null}

      {showTimeSaved ? <TimeSavedPanel /> : null}

      {showBeeBadges ? <BeeBadgesPanel limit={6} compact /> : null}

      {showInsights ? (
        <div
          className={cn(
            showPerformanceTier && showRecentTasks
              ? "v4-mobile-card-slider v4-mobile-card-slider--wide"
              : "grid grid-cols-1 gap-5",
          )}
        >
          {showPerformanceTier ? (
            <V4Card className="v4-card-interactive">
              <V4CardHeader title="Performance by tier" description="Share of agents in the hive (API summary)" as="h3" />
              <div className="mt-2">
                {tierBars.map((row) => (
                  <V4BarRow key={row.key} label={row.label} value={`${row.pct}% · ${row.count}`} pct={row.pct} />
                ))}
              </div>
            </V4Card>
          ) : null}
          {showRecentTasks ? (
            <V4Card className="v4-card-interactive">
              <V4CardHeader title="Recent tasks" description={`Latest ${Math.min(8, recentTasks.length)} rows from /api/v1/tasks`} as="h3" />
              <ul className="mt-2 divide-y divide-(--qs-border)">
                {recentTasks.length === 0 ? (
                  <li className="py-6 text-center text-sm text-(--qs-text-3)">No tasks synced yet.</li>
                ) : (
                  recentTasks.slice(0, 8).map((t) => (
                    <li key={t.id} className="flex gap-3 py-3 transition hover:bg-white/[0.03]">
                      <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", statusDotClass(t.status))} aria-hidden />
                      <div className="min-w-0 flex-1">
                        <Link href="/tasks" className="truncate text-sm text-(--qs-text) hover:text-pollen">
                          {t.title}
                        </Link>
                        <p className="mt-0.5 text-[11px] text-(--qs-text-3)">{taskStatusBrief(t.status)}</p>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </V4Card>
          ) : null}
        </div>
      ) : null}

      {showQueenMission ? (
        <V4QueenMission
          brief={missionBrief}
          onBriefChange={onMissionBriefChange}
          onRun={onRunMission}
          busy={missionBusy}
          error={missionErr}
        />
      ) : null}
    </V4PageCanvas>
  );
}
