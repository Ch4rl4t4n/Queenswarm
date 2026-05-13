export interface DashboardSummary {
  generated_at: string;
  agents: {
    total: number;
    by_status: Record<string, number>;
    by_hive_tier: Record<string, number>;
  };
  tasks: {
    pending: number;
  };
}

export interface AgentRow {
  id: string;
  name: string;
  role: string;
  status: string;
  pollen_points: number;
  performance_score?: number;
  swarm_id?: string | null;
  /** Sub-swarm display name once the bee joins a colony (omit when ``swarm_id`` is unset). */
  swarm_name?: string | null;
  /** Backend ``SwarmPurpose`` string: scout | eval | simulation | action */
  swarm_purpose?: string | null;
  current_task_id?: string | null;
  current_task_title?: string | null;
  has_universal_config?: boolean;
  /** orchestrator | manager | worker | omitted for legacy bees */
  hive_tier?: string | null;
}

export interface SubSwarmRow {
  id: string;
  name: string;
  purpose: string;
  member_count: number;
  total_pollen: number;
  is_active: boolean;
  last_global_sync_at?: string | null;
}

export interface TaskRow {
  id: string;
  title: string;
  status: string;
  priority: number;
  task_type: string;
  swarm_id?: string | null;
  agent_id?: string | null;
  agent_name?: string | null;
  payload?: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
  error_msg?: string | null;
  confidence_score?: number | null;
  cost_usd?: number | null;
  output_format?: string | null;
}

export interface RecipeRow {
  id: string;
  name: string;
  description: string | null;
  verified_at?: string | null;
  topic_tags: string[];
}

export interface WorkflowRow {
  id: string;
  original_task_text: string;
  status: string;
  total_steps: number;
  completed_steps: number;
  matching_recipe_id?: string | null;
}

export interface SimulationRow {
  id: string;
  result_type: string;
  confidence_pct?: number;
  task_id?: string | null;
  created_at?: string | null;
}

/** `/operator/costs/summary` aggregate for dashboard spend tiles. */
export interface OperatorCostSummary {
  window_days: number;
  series: { day: string; model: string; spend_usd: number }[];
}

/** Ephemeral breaker preview (`POST /operator/preview-decomposition`). */
export interface PreviewWorkflowStep {
  step_order: number;
  description: string;
  agent_role: string;
  guardrail_summary: string;
  guardrails: Record<string, unknown>;
  evaluation_criteria: Record<string, unknown>;
}

export interface RecipeMatchBrief {
  name: string;
  similarity: number;
  postgres_recipe_id: string | null;
}

export interface PreviewDecompositionResponse {
  steps: PreviewWorkflowStep[];
  decomposition_rationale: string;
  parallel_groups: number[][];
  estimated_duration_sec: number | null;
  decomposition_cost_usd: number;
  recipe_match: RecipeMatchBrief | null;
}

export interface OperatorIntakeResponse {
  workflow_id: string;
  task_id: string;
  swarm_id: string;
  celery_task_id: string | null;
  execution: "queued" | "inline" | "skipped";
}

/** `/dashboard/swarm-board` — sub-swarm cards + waggle feed. */
export interface SwarmBoardCard {
  id: string;
  slug: string;
  display_name: string;
  lane: string;
  purpose: string;
  description: string;
  member_count: number;
  total_pollen: number;
  avg_performance_pct: number;
  queen_label: string;
  is_active: boolean;
  last_global_sync_at: string | null;
  last_sync_seconds_ago: number | null;
}

export interface WaggleFeedItem {
  id: string;
  source_label: string;
  source_lane: string;
  target_label: string;
  target_lane: string;
  message: string;
  occurred_at: string;
  seconds_ago: number;
}

export interface SwarmBoardResponse {
  generated_at: string;
  hive_sync_interval_sec: number;
  sub_swarms: SwarmBoardCard[];
  waggle_feed: WaggleFeedItem[];
}

/** `/dashboard/task-queue` — backlog list with step progress. */
export interface TaskQueueItem {
  id: string;
  short_id: string;
  title: string;
  status: string;
  task_type: string;
  swarm_label: string;
  lane: string;
  steps_done: number;
  steps_total: number;
  progress_pct: number;
  updated_at: string;
  seconds_ago: number;
}

export interface TaskQueueResponse {
  generated_at: string;
  running_count: number;
  pending_count: number;
  completed_today_count: number;
  tasks: TaskQueueItem[];
}

/** `/dashboard/workflows` — featured DAG + list rows. */
export type WorkflowDagState = "completed" | "active" | "upcoming" | "failed";
export type WorkflowHexTone = "cyan" | "pollen" | "alert" | "success";

export interface WorkflowDagStep {
  id: string;
  step_order: number;
  label: string;
  description_excerpt: string;
  agent_role: string;
  status: string;
  dag_state: WorkflowDagState;
  hex_tone: WorkflowHexTone;
}

export interface WorkflowFeatured {
  id: string;
  short_id: string;
  title: string;
  status: string;
  ui_status: string;
  total_steps: number;
  completed_steps: number;
  progress_pct: number;
  footer_line: string;
  seconds_ago: number;
  updated_at: string;
  tags: string[];
  lane: string;
  task_id: string | null;
  steps: WorkflowDagStep[];
}

export interface WorkflowListItem {
  id: string;
  short_id: string;
  title: string;
  status: string;
  ui_status: string;
  tags: string[];
  lane: string;
  steps_done: number;
  steps_total: number;
  progress_pct: number;
  seconds_ago: number;
  updated_at: string;
  task_id: string | null;
}

export interface WorkflowsDashboardResponse {
  generated_at: string;
  featured: WorkflowFeatured | null;
  workflows: WorkflowListItem[];
}
