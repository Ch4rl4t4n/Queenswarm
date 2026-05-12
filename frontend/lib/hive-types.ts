export interface DashboardSummary {
  generated_at: string;
  agents: { total: number; by_status: Record<string, number> };
  swarms: { total: number; by_purpose: Record<string, number> };
  tasks: { pending: number };
  recipes: { total: number };
  pollen: {
    system_total_estimate: number;
    earned_last_24h: number;
    window_hours: number;
  };
  waggle_dances: {
    from_swarm: string;
    signal: string;
    topic: string;
    ts: string;
  }[];
  leaderboard_preview: {
    rank: number;
    agent_id: string;
    name: string;
    pollen: number;
    role: string;
    performance: number;
  }[];
}

export interface AgentRow {
  id: string;
  name: string;
  role: string;
  status: string;
  pollen_points: number;
  performance_score?: number;
  swarm_id?: string | null;
  current_task_id?: string | null;
  current_task_title?: string | null;
  has_universal_config?: boolean;
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
