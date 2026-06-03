/** Shared Execution Studio types for panel components. */

export type ExecutionMode = "draft" | "simulate" | "live";

export interface StudioPolicy {
  default_mode: ExecutionMode;
  live_requires_approval: boolean;
  simulate_allows_read_calls: boolean;
  codebase_default_mode: ExecutionMode;
  live_codebase_requires_approval: boolean;
  codebase_auto_approve_enabled: boolean;
  codebase_pr_only: boolean;
}

export interface SetupStep {
  id: string;
  title: string;
  detail: string;
}

export interface StudioConnection {
  id: string;
  slug: string;
  display_name: string;
  auth_type: string;
  status: "active" | "needs_credentials" | "ready_to_test" | "inactive";
  is_active: boolean;
  tools_count: number;
  allowed_manager_slugs: string[];
  template_id: string | null;
  agent_usage?: string | null;
  doc_url?: string | null;
  last_tested_at?: string | null;
}

export interface CodebaseBudget {
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

export interface CodebaseLane {
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

export interface PendingProposal {
  id: string;
  title: string;
  description: string;
  proposed_by_role: string;
  risk_level: string;
  created_at?: string | null;
  goal_excerpt?: string;
}

export interface HandledProposal extends PendingProposal {
  status: "approved" | "rejected" | "pending";
  reviewed_at?: string | null;
  reviewed_by_subject?: string | null;
  handoff_session_id?: string | null;
}

export interface BrowserFallbackLane {
  enabled: boolean;
  role: string;
  lane: string;
  description: string;
  sessions_api: string;
  execute_api?: string;
  supervisor_role: string;
}

export interface PendingLiveAction {
  type: "browser" | "external";
  at?: string;
  message?: string;
  connector_slug?: string;
  tool_name?: string | null;
  proposal_id?: string | null;
  supervisor_session_id?: string | null;
}

export interface PendingApprovalsSnapshot {
  count: number;
  browser_pending: number;
  external_pending: number;
  codebase_pending: number;
  live_actions: PendingLiveAction[];
}

/** Remove a cleared live action from the pending approvals snapshot. */
export function clearPendingLiveAction(
  approvals: PendingApprovalsSnapshot,
  action: PendingLiveAction,
): PendingApprovalsSnapshot {
  const live_actions = approvals.live_actions.filter((row) => {
    if (action.type === "browser") return row.type !== "browser";
    return !(
      row.type === "external" &&
      row.connector_slug === action.connector_slug &&
      (row.tool_name ?? "search") === (action.tool_name ?? "search")
    );
  });
  const browser_pending = live_actions.filter((row) => row.type === "browser").length;
  const external_pending = live_actions.filter((row) => row.type === "external").length;
  const count = browser_pending + external_pending + Math.max(0, approvals.codebase_pending ?? 0);
  return { ...approvals, live_actions, browser_pending, external_pending, count };
}
