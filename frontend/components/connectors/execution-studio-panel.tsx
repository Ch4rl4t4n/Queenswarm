"use client";

import {
  BookOpen,
  Lightbulb,
  Plug,
  RefreshCw,
  Rocket,
  Zap,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ExecutionStudioSupervisorContext } from "@/components/connectors/execution-studio-supervisor-context";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import type {
  ActivityTelemetry,
  MediaRegistry,
  StudioActivity,
} from "@/components/connectors/execution-studio-analytics-panel";
import type { SuperRouterSnapshot } from "@/components/connectors/execution-studio-super-routers-panel";
import { VirtualCompanySetupCard } from "@/components/hive/virtual-company-setup-card";
import { HiveSubnavRow } from "@/components/hive/hive-subnav-row";
import { V4CardHeader } from "@/components/ui/v4";
import type { StudioNotifications } from "@/components/connectors/execution-studio-notifications-panel";
import { HiveApiError, hiveGet } from "@/lib/api";
import {
  executionStudioSectionFromQuery,
  executionStudioWorkspaceFromHash,
  integrationsScrollTargetFromHash,
  type ExecutionStudioWorkspaceSection,
} from "@/lib/integrations-routes";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";
import type {
  BrowserFallbackLane,
  PendingApprovalsSnapshot,
} from "@/lib/execution-studio-shared-types";

const ExecutionStudioNotificationsPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-notifications-panel").then((m) => ({
      default: m.ExecutionStudioNotificationsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioCodebaseLanePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-codebase-lane-panel").then((m) => ({
      default: m.ExecutionStudioCodebaseLanePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[12rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioPolicyPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-policy-panel").then((m) => ({
      default: m.ExecutionStudioPolicyPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[5rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioLiveApprovalsPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-live-approvals-panel").then((m) => ({
      default: m.ExecutionStudioLiveApprovalsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioAnalyticsPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-analytics-panel").then((m) => ({
      default: m.ExecutionStudioAnalyticsPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[12rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioStackPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-stack-panel").then((m) => ({
      default: m.ExecutionStudioStackPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[16rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioSuperRoutersPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-super-routers-panel").then((m) => ({
      default: m.ExecutionStudioSuperRoutersPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioManualPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-manual-panel").then((m) => ({
      default: m.ExecutionStudioManualPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="space-y-4" aria-hidden><div className="qs-bubble min-h-[6rem] animate-pulse bg-white/5 p-4" /></div>,
  },
);

const ExecutionStudioInnovationPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-innovation-panel").then((m) => ({
      default: m.ExecutionStudioInnovationPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioPublishQueuePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-publish-queue-panel").then((m) => ({
      default: m.ExecutionStudioPublishQueuePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioSocialPublishPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-social-publish-panel").then((m) => ({
      default: m.ExecutionStudioSocialPublishPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioPublishPerformancePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-publish-performance-panel").then((m) => ({
      default: m.ExecutionStudioPublishPerformancePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioTradingContentHybridPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-trading-content-hybrid-panel").then((m) => ({
      default: m.ExecutionStudioTradingContentHybridPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioTradingCockpitPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-trading-cockpit-panel").then((m) => ({
      default: m.ExecutionStudioTradingCockpitPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[12rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioMediaAgencyPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-media-agency-panel").then((m) => ({
      default: m.ExecutionStudioMediaAgencyPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioLiveLanePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-live-lane-panel").then((m) => ({
      default: m.ExecutionStudioLiveLanePanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioMicroSaasFactoryPanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-micro-saas-factory-panel").then((m) => ({
      default: m.ExecutionStudioMicroSaasFactoryPanel,
    })),
  {
    ssr: false,
    loading: () => <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />,
  },
);

const ExecutionStudioSkillForgePanel = dynamic(
  () =>
    import("@/components/connectors/execution-studio-skill-forge-panel").then((m) => ({
      default: m.ExecutionStudioSkillForgePanel,
    })),
  {
    ssr: false,
    loading: () => null,
  },
);

type ExecutionMode = "draft" | "simulate" | "live";
type ConnectionStatus = "active" | "needs_credentials" | "ready_to_test" | "inactive";

interface StudioPolicy {
  default_mode: ExecutionMode;
  live_requires_approval: boolean;
  simulate_allows_read_calls: boolean;
  codebase_default_mode: ExecutionMode;
  live_codebase_requires_approval: boolean;
  codebase_pr_only: boolean;
}

interface CodebaseBudget {
  session_cap_usd: number;
  daily_run_limit: number;
  runs_today: number;
  remaining_runs_today: number;
  routing_mode: string;
  models: Record<string, string>;
  simulate_first: boolean;
  pr_only: boolean;
  cursor_role: string;
}

interface CodebaseLane {
  lane: string;
  queen_maintainer_enabled: boolean;
  budget?: CodebaseBudget;
  tech_health: {
    health_score?: number;
    signals: string[];
    backend_pinned_deps: number;
    frontend_deps: number;
  };
  maintainer_routine: {
    enabled: boolean;
    routine_id: string | null;
  };
  github_repo: {
    owner: string;
    repo: string;
    configured: boolean;
  };
  repo_connector: StudioConnection | null;
  pr_only: boolean;
  denylist_prefixes: string[];
  agent_roles: string[];
  agent_skills: string[];
  setup_steps: SetupStep[];
}

interface StudioConnection {
  id: string;
  slug: string;
  display_name: string;
  auth_type: string;
  status: ConnectionStatus;
  is_active: boolean;
  tools_count: number;
  allowed_manager_slugs: string[];
  template_id: string | null;
  agent_usage?: string | null;
  doc_url?: string | null;
  last_tested_at?: string | null;
}

interface StudioPackTemplate {
  template_id: string;
  slug: string;
  display_name: string;
  installed: boolean;
}

interface StudioPack {
  id: string;
  label: string;
  description: string;
  templates: StudioPackTemplate[];
}

interface SetupStep {
  id: string;
  title: string;
  detail: string;
}

interface PendingProposal {
  id: string;
  title: string;
  description: string;
  proposed_by_role: string;
  risk_level: string;
  created_at?: string | null;
  goal_excerpt?: string;
}

interface StudioOverview {
  enabled: boolean;
  policy: StudioPolicy;
  notifications?: StudioNotifications;
  stats: Record<string, number>;
  connections: StudioConnection[];
  packs: StudioPack[];
  setup_steps: SetupStep[];
  codebase: CodebaseLane;
  manual?: { version: string; title: string; summary: string; section_count: number };
  pending_codebase_proposals?: PendingProposal[];
  pending_approvals?: PendingApprovalsSnapshot;
  recent_activity?: StudioActivity[];
  activity_telemetry?: ActivityTelemetry;
  media_registry?: MediaRegistry;
  browser_fallback?: BrowserFallbackLane;
  super_routers?: SuperRouterSnapshot;
}

type StudioPanelView = "workspace" | "manual";

const WORKSPACE_SECTIONS: { id: ExecutionStudioWorkspaceSection; label: string; icon: typeof Rocket }[] = [
  { id: "overview", label: "Overview", icon: Rocket },
  { id: "publish", label: "Publish", icon: Zap },
  { id: "lanes", label: "Lanes", icon: Plug },
  { id: "innovation", label: "Innovation", icon: Lightbulb },
  { id: "stack", label: "Connections", icon: RefreshCw },
  { id: "analytics", label: "Analytics", icon: BookOpen },
];

interface ExecutionStudioPanelProps {
  onOpenMarketplace?: () => void;
  onOpenHub?: () => void;
}

function modeLabel(mode: ExecutionMode): string {
  if (mode === "draft") return "Draft — preview only";
  if (mode === "simulate") return "Simulate — dry-run writes";
  return "Live — real upstream calls";
}

export function ExecutionStudioPanel({ onOpenMarketplace, onOpenHub }: ExecutionStudioPanelProps) {
  const searchParams = useSearchParams();
  const [overview, setOverview] = useState<StudioOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executeResult, setExecuteResult] = useState<string | null>(null);
  const [panelView, setPanelView] = useState<StudioPanelView>("workspace");
  const [workspaceSection, setWorkspaceSection] = useState<ExecutionStudioWorkspaceSection>("overview");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await hiveGet<StudioOverview>("execution-studio/overview");
      setOverview(data);
    } catch (exc) {
      setError(exc instanceof HiveApiError ? exc.message : "Failed to load Execution Studio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash : "";
    const fromQuery = executionStudioSectionFromQuery(searchParams.get("section"));
    const fromHash = executionStudioWorkspaceFromHash(hash);
    const section = fromQuery ?? fromHash;
    if (section) {
      setPanelView("workspace");
      setWorkspaceSection(section);
    }
  }, [searchParams]);

  useEffect(() => {
    if (panelView !== "workspace") {
      return;
    }
    const targetId = integrationsScrollTargetFromHash(typeof window !== "undefined" ? window.location.hash : "");
    if (!targetId) {
      return;
    }
    const behavior = scrollBehaviorForMotion();
    const attemptScroll = (retries: number): void => {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior, block: "start" });
        return;
      }
      if (retries > 0) {
        window.setTimeout(() => attemptScroll(retries - 1), 100);
      }
    };
    window.setTimeout(() => attemptScroll(24), 80);
  }, [panelView, workspaceSection]);

  const stats = overview?.stats ?? {};
  const activeCount = stats.active ?? 0;
  const pendingCount = (stats.needs_credentials ?? 0) + (stats.ready_to_test ?? 0);

  const pendingLiveActions = useMemo(
    () => overview?.pending_approvals?.live_actions ?? [],
    [overview?.pending_approvals?.live_actions],
  );

  const supervisorSessionIds = useMemo(
    () =>
      pendingLiveActions
        .map((action) => action.supervisor_session_id)
        .filter((sessionId): sessionId is string => Boolean(sessionId)),
    [pendingLiveActions],
  );

  return (
    <div className="v4-execution-studio-shell">
      <V4CardHeader
        as="h3"
        title="Execution Studio"
        description="Connect external apps, govern draft → simulate → live execution, and wire tools into supervisor tasks."
        actions={
          <HiveRefreshButton busy={loading} onClick={() => void load()} />
        }
      />

      {error ? (
        <div className="flex shrink-0 items-center justify-between gap-2 rounded-xl border border-(--qs-red)/35 bg-(--qs-red)/10 px-3 py-2 text-xs text-(--qs-red)">
          <span>{error}</span>
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm shrink-0" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      <VirtualCompanySetupCard onChanged={() => void load()} />

      <HiveSubnavRow
        items={[
          { id: "workspace", label: "Workspace", icon: Rocket },
          {
            id: "manual",
            label: "Manual",
            icon: BookOpen,
            badge: overview?.manual?.section_count || undefined,
          },
        ]}
        activeId={panelView}
        onChange={(id) => setPanelView(id as StudioPanelView)}
        ariaLabel="Execution Studio views"
        menuKey="execution-studio-panel"
      />

      <ExecutionStudioSupervisorContext sessionIds={supervisorSessionIds} />

      <ExecutionStudioLiveApprovalsPanel
        pendingApprovals={overview?.pending_approvals}
        browserFallback={overview?.browser_fallback}
        defaultMode={overview?.policy.default_mode ?? "simulate"}
        liveRequiresApproval={overview?.policy.live_requires_approval ?? true}
        loading={loading}
        onPendingApprovalsUpdate={(pending) =>
          setOverview((prev) => (prev ? { ...prev, pending_approvals: pending } : prev))
        }
        onError={setError}
        onExecuteResult={setExecuteResult}
        onReloadOverview={load}
        onNavigateToWorkspace={() => setPanelView("workspace")}
      />

      {panelView === "manual" ? <ExecutionStudioManualPanel onError={setError} /> : null}

      {panelView === "workspace" ? (
      <>
      <HiveSubnavRow
        items={WORKSPACE_SECTIONS.map(({ id, label, icon }) => ({ id, label, icon }))}
        activeId={workspaceSection}
        onChange={(id) => setWorkspaceSection(id as ExecutionStudioWorkspaceSection)}
        ariaLabel="Execution Studio workspace sections"
        menuKey="execution-studio-workspace"
      />

      {workspaceSection === "overview" ? (
      <>
      <div className="grid shrink-0 gap-3 md:grid-cols-3">
        <article className="v4-dream-cycle-card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">Ready</p>
          <p className="mt-1 font-mono text-2xl text-(--qs-green)">{activeCount}</p>
          <p className="mt-1 text-xs text-(--qs-text-3)">Active connections agents can invoke</p>
        </article>
        <article className="v4-dream-cycle-card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">Pending setup</p>
          <p className="mt-1 font-mono text-2xl text-pollen">{pendingCount}</p>
          <p className="mt-1 text-xs text-(--qs-text-3)">Need credentials or activation test</p>
        </article>
        <article className="v4-dream-cycle-card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-(--qs-text-3)">Default mode</p>
          <p className="mt-1 text-sm font-semibold text-(--qs-text)">{overview?.policy.default_mode ?? "simulate"}</p>
          <p className="mt-1 text-xs text-(--qs-text-3)">{modeLabel(overview?.policy.default_mode ?? "simulate")}</p>
        </article>
      </div>
      </>
      ) : null}

      {workspaceSection === "publish" ? (
      <>
      <ExecutionStudioPublishQueuePanel onError={setError} />

      <ExecutionStudioSocialPublishPanel onError={setError} onOpenHub={onOpenHub} />

      <ExecutionStudioPublishPerformancePanel onError={setError} />

      <ExecutionStudioTradingContentHybridPanel onError={setError} />

      <ExecutionStudioTradingCockpitPanel onError={setError} />
      </>
      ) : null}

      {workspaceSection === "lanes" ? (
      <>
      <ExecutionStudioLiveLanePanel onError={setError} />

      <ExecutionStudioMediaAgencyPanel onError={setError} />

      <ExecutionStudioMicroSaasFactoryPanel onError={setError} />

      <ExecutionStudioSkillForgePanel onError={setError} />

      {overview?.codebase ? (
        <ExecutionStudioCodebaseLanePanel
          codebase={overview.codebase}
          policy={overview.policy}
          pendingProposals={overview.pending_codebase_proposals}
          loading={loading}
          onPolicyUpdate={(policy) => setOverview((prev) => (prev ? { ...prev, policy } : prev))}
          onError={setError}
          onReloadOverview={load}
          onExecuteResult={setExecuteResult}
        />
      ) : null}
      </>
      ) : null}

      {workspaceSection === "analytics" ? (
      <>
      <ExecutionStudioAnalyticsPanel
        activityTelemetry={overview?.activity_telemetry}
        recentActivity={overview?.recent_activity}
        mediaRegistry={overview?.media_registry}
        onError={setError}
        onReloadOverview={load}
      />

      <ExecutionStudioSuperRoutersPanel superRouters={overview?.super_routers} />

      {overview?.policy ? (
        <ExecutionStudioPolicyPanel
          policy={overview.policy}
          loading={loading}
          onPolicyUpdate={(policy) => setOverview((prev) => (prev ? { ...prev, policy } : prev))}
          onError={setError}
        />
      ) : null}

      <ExecutionStudioNotificationsPanel
        notifications={overview?.notifications}
        loading={loading}
        onNotificationsChange={(notifications) => setOverview((prev) => (prev ? { ...prev, notifications } : prev))}
        onError={setError}
        onReloadOverview={load}
      />
      </>
      ) : null}

      {workspaceSection === "innovation" ? <ExecutionStudioInnovationPanel /> : null}

      {workspaceSection === "stack" ? (
      <>
      <div className="flex shrink-0 flex-wrap gap-2">
        {onOpenMarketplace ? (
          <button type="button" className="qs-btn qs-btn--primary qs-btn--sm gap-2" onClick={onOpenMarketplace}>
            <Plug className="h-4 w-4" aria-hidden />
            Add connection
          </button>
        ) : null}
        {onOpenHub ? (
          <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" onClick={onOpenHub}>
            <Zap className="h-4 w-4" aria-hidden />
            Connector hub
          </button>
        ) : null}
      </div>

      <ExecutionStudioStackPanel
        connections={overview?.connections ?? []}
        packs={overview?.packs ?? []}
        setupSteps={overview?.setup_steps ?? []}
        defaultMode={overview?.policy.default_mode ?? "simulate"}
        loading={loading}
        executeResult={executeResult}
        onError={setError}
        onExecuteResult={setExecuteResult}
        onReloadOverview={load}
      />
      </>
      ) : null}
      </>
      ) : null}
    </div>
  );
}
