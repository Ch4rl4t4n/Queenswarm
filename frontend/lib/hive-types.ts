export interface WaggleDanceSummaryRow {
  ts: string;
  from_swarm: string;
  signal: string;
  topic: string;
}

/** JWT-guarded ``GET /api/v1/system/status`` gauges for KPI tiles. */
export interface SystemStatusPayload {
  redis_ok: boolean;
  celery_ok: boolean;
  celery_workers_up?: number;
  celery_active_tasks?: number;
  celery_reserved_tasks?: number;
  db_ok: boolean;
  llm_ok: boolean;
  llm_grok: boolean;
  llm_anthropic: boolean;
  agents_total: number;
  agents_running: number;
  tasks_running: number;
  tasks_pending: number;
  host_cpu_percent: number;
  host_memory_percent: number;
  host_disk_percent: number;
  llm_concurrency_limit: number;
  llm_in_flight: number;
  simulation_concurrency_limit: number;
  simulation_in_flight: number;
  simulation_enabled: boolean;
  simulation_tasks_running: number;
  simulation_tasks_pending: number;
  resource_pressure: boolean;
  resource_pressure_reason: string;
}

/** Masked row from ``GET /api/v1/llm-keys``. */
export interface LlmKeyMaskRow {
  id: string;
  provider: "grok" | "anthropic" | "openai" | "deepgram" | "elevenlabs";
  label: string;
  api_key_masked: string;
  model_default: string | null;
  is_active?: boolean;
  is_primary?: boolean;
  from_vault?: boolean;
}

/** Operator notification channel row from ``GET /api/v1/notifications``. */
export interface NotificationChannelListRow {
  id: string;
  channel_type: "email" | "sms" | "discord" | "telegram";
  label: string;
  config_masked: Record<string, unknown>;
  is_active: boolean;
}

/** Static catalog entry from ``GET /api/v1/external-apis/providers``. */
export interface ExternalProviderMeta {
  id: string;
  label: string;
  base_url?: string | null;
}

/** Persisted credential row from ``GET /api/v1/external-apis``. */
export interface ExternalApiStoredRow {
  id: string;
  provider: string;
  label: string;
  is_active: boolean;
  base_url: string | null;
  credentials_masked: Record<string, unknown>;
}

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
  waggle_dances?: WaggleDanceSummaryRow[];
}

export interface TenantViewRow {
  id: string;
  slug: string;
  name: string;
  role: string;
  is_active: boolean;
  platform_mode?: string;
}

export interface TenantListPayload {
  current_tenant_id: string | null;
  tenants: TenantViewRow[];
}

export interface TeamMemberRow {
  id: string;
  user_id: string;
  email: string;
  role: string;
  joined_at: string;
  can_manage: boolean;
}

export interface TeamInviteRow {
  id: string;
  email: string;
  role: string;
  status: string;
  invite_token: string;
  created_at: string;
}

export interface TeamOverviewPayload {
  tenant_id: string;
  tenant_role: string;
  permissions: string[];
  members: TeamMemberRow[];
  invites: TeamInviteRow[];
}

export interface BillingUsageSnapshot {
  tenant_id: string;
  tier: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  usage: Record<string, number>;
  limits: Record<string, number>;
  usage_health: Record<
    string,
    {
      value: number;
      soft_limit: number;
      hard_limit: number;
      soft_exceeded: boolean;
      hard_exceeded: boolean;
      soft_pct: number;
      hard_pct: number;
    }
  >;
  features: Record<string, boolean>;
  upgrade_recommended: boolean;
}

export interface BillingPlansPayload {
  current_tier: string;
  plans: Array<{
    tier: string;
    label: string;
    limits: Record<string, number>;
    features: Record<string, boolean>;
  }>;
  checkout_ready: boolean;
  pro_checkout_ready?: boolean;
  pro_price_eur_cents?: number;
  enterprise_checkout_ready?: boolean;
  enterprise_price_eur_cents?: number;
  message: string;
}

export interface StripeConfigStatus {
  checkout_ready: boolean;
  webhook_ready: boolean;
  secret_key_masked: string | null;
  webhook_secret_masked: string | null;
  secret_key_source: string;
  webhook_secret_source: string;
  webhook_url: string;
  env_fallback_active: boolean;
}

export interface PublicShareRow {
  id: string;
  resource_type: "output" | "session" | "swarm";
  resource_id: string;
  share_token: string;
  is_active: boolean;
  access_count: number;
  expires_at: string | null;
  created_at: string;
  public_url: string;
}

export interface AgentRow {
  id: string;
  name: string;
  role: string;
  status: string;
  pollen_points: number;
  performance_score?: number;
  swarm_id?: string | null;
  /** Sub-swarm row id when API exposes placement (Phase R filter / hex stroke). */
  sub_swarm_id?: string | null;
  /** Optional swarm kind label from API joins. */
  swarm_type?: string | null;
  /** Nested swarm payload when hydration includes it. */
  swarm?: { name?: string } | null;
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

export interface SubAgentSessionRow {
  id: string;
  role: string;
  status: string;
  runtime_mode: string;
  toolset: string[];
  short_memory: Record<string, unknown>;
  spawn_order: number;
  started_at: string | null;
  completed_at: string | null;
  last_output: string | null;
  error_text: string | null;
  celery_task_id?: string | null;
  celery_enqueued_at?: string | null;
  self_heal_attempts?: number | null;
  requeue_count?: number | null;
}

export interface SubAgentJobStatusRow {
  sub_agent_session_id: string;
  supervisor_session_id: string;
  celery_task_id: string | null;
  task_name: string;
  state: string;
  ready: boolean;
  successful: boolean | null;
  result: Record<string, unknown> | null;
  error: string | null;
  enqueued_at: string | null;
  self_heal_attempts: number | null;
}

export interface SupervisorSessionAuditLogRow {
  id: string;
  tenant_id: string;
  action: string;
  target_type: string;
  target_ref: string;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface SupervisorSessionContextHistoryRow {
  audit_id: string;
  action: string;
  created_at: string;
  context_diff: {
    added?: Record<string, unknown>;
    removed?: Record<string, unknown>;
    changed?: Record<string, { before: unknown; after: unknown }>;
    nested?: Record<
      string,
      {
        added?: Record<string, unknown>;
        removed?: Record<string, unknown>;
        changed?: Record<string, { before: unknown; after: unknown }>;
        nested?: Record<string, unknown>;
        added_items?: unknown[];
        removed_items?: unknown[];
        item_changes?: Array<Record<string, unknown>>;
        before_len?: number;
        after_len?: number;
        before?: unknown;
        after?: unknown;
      }
    >;
  };
  session_status: string | null;
  control_action: string | null;
  decision: string | null;
}

export interface SupervisorSessionRow {
  id: string;
  goal: string;
  status: string;
  runtime_mode: string;
  created_by_subject: string | null;
  context_summary: Record<string, unknown>;
  swarm_id: string | null;
  task_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
  sub_agents: SubAgentSessionRow[];
}

export interface SupervisorSharedContextRow {
  session_id: string;
  enabled: boolean;
  retrieval_contract: string;
  matched_sections: string[];
  sections: Record<string, unknown>;
  relevance_scores?: Record<string, number> | null;
  pruned_items: number;
  prompt_block: string;
  context_summary: Record<string, unknown>;
}

export interface SupervisorRoutineRow {
  id: string;
  name: string;
  goal_template: string;
  schedule_kind: string;
  interval_seconds: number | null;
  cron_expr: string | null;
  runtime_mode: string;
  roles: string[];
  retrieval_contract: string | null;
  skills: string[];
  context_payload: Record<string, unknown>;
  status: string;
  is_active: boolean;
  created_by_subject: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupervisorControlSummaryRow {
  sessions_total: number;
  status_counts: Record<string, number>;
  running_sessions: number;
  needs_input_sessions: number;
  completed_sessions: number;
  routines_total: number;
  active_routines: number;
  due_routines: number;
  inprocess_active_sessions?: number;
  durable_active_sessions?: number;
  durable_queued_sub_agents?: number;
}

export interface SwarmAutonomySummaryRow {
  tenant_id: string;
  autonomy_mode: string;
  active_long_horizon_routines: number;
  pending_memory_approvals: number;
  pending_initiative_approvals: number;
  average_strategy_score: number;
  reflection_entries: number;
  status: string;
}

export interface AgentSuggestionRow {
  id: string;
  supervisor_session_id: string | null;
  sub_agent_session_id: string | null;
  proposal_type: "skill_proposal" | "workflow_optimization" | "prompt_optimization" | "tooling_proposal" | string;
  proposed_by_role: string;
  title: string;
  description: string;
  proposal_payload: Record<string, unknown>;
  risk_level: "low" | "medium" | "high" | string;
  impact_score: number;
  status: "pending" | "approved" | "rejected" | string;
  requires_manual_approval: boolean;
  evaluation_reason: string | null;
  reviewed_by_subject: string | null;
  reviewed_at: string | null;
  implemented_at: string | null;
  created_at: string;
}

export interface SupervisorSessionEventRow {
  id: string;
  supervisor_session_id: string;
  sub_agent_session_id: string | null;
  event_type: string;
  level: string;
  message: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  created_at: string;
}

export interface BrowserAutomationActionRow {
  id: string;
  browser_session_id: string;
  action_type: string;
  status: string;
  requires_approval: boolean;
  payload: Record<string, unknown>;
  result_summary: string | null;
  occurred_at: string;
}

export interface BrowserAutomationSessionRow {
  id: string;
  supervisor_session_id: string | null;
  sub_agent_session_id: string | null;
  mode: "headless" | "visible" | string;
  status: string;
  start_url: string | null;
  current_url: string | null;
  allowed_domains: string[];
  blocked_reason: string | null;
  expires_at: string | null;
  max_actions: number;
  actions_used: number;
  pending_approval_action: Record<string, unknown>;
  last_snapshot_text: string | null;
  last_screenshot_base64: string | null;
  is_headless: boolean;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
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

/** Celery / Postgres mirrored async workflow poll (`GET /jobs/{id}`). */
export interface HiveAsyncJobStatusPayload {
  celery_task_id: string;
  state: string;
  ready: boolean;
  successful: boolean | null;
  workflow_result?: Record<string, unknown> | null;
  error?: string | null;
  postgres_ledger?: {
    id: string;
    swarm_id: string;
    workflow_id: string;
    hive_task_id?: string | null;
    lifecycle: string;
    created_at: string;
    updated_at: string;
    finished_at?: string | null;
    error_preview?: string | null;
  } | null;
}

export interface RecipeRow {
  id: string;
  name: string;
  description: string | null;
  verified_at?: string | null;
  topic_tags: string[];
  orchestration_template?: string | null;
  pattern_tags?: string[];
  pattern_labels?: string[];
  success_count?: number;
  fail_count?: number;
  avg_pollen_earned?: number;
}

export interface RecipePatternStackRow {
  id: string;
  label: string;
  pattern_tags: string[];
  pattern_labels: string[];
}

/** ``GET /api/v1/memory/episodic/timeline`` */
export interface EpisodicMemoryItemRow {
  id: string;
  kind: string;
  occurred_at: string;
  title: string;
  summary: string;
  session_id: string | null;
  metadata: Record<string, unknown>;
}

export interface EpisodicMemoryPayload {
  retention_days: number;
  item_count: number;
  items: EpisodicMemoryItemRow[];
}

export interface EpisodicSummaryPayload {
  retention_days: number;
  counts: {
    session_events: number;
    dream_insights: number;
    dump_sleep_batches: number;
    session_summaries: number;
  };
  total_items: number;
  latest_at: string | null;
}

/** Semantic recipe hit (`GET /recipes/search`). */
export interface RecipeSemanticHit {
  chroma_document_id: string;
  similarity: number;
  vector_similarity?: number | null;
  graph_score?: number | null;
  distance?: number | null;
  document_preview: string;
  metadata: Record<string, unknown>;
  postgres_recipe_id?: string | null;
  postgres_row?: RecipeRow | null;
}

/** Imitation gate config (`GET /recipes/match-config`). */
export interface RecipeMatchConfigPayload {
  match_threshold: number;
  min_search_similarity: number;
  hybrid_scoring_enabled: boolean;
  hybrid_vector_weight: number;
  hybrid_graph_weight: number;
}

/** Skill export bundle (`POST /recipes/{id}/export-skill`). */
export interface SkillExportFile {
  path: string;
  content: string;
}

export interface SkillExportMeta {
  source: string;
  recipe_id: string;
  recipe_name: string;
  slug: string;
  verified: boolean;
  verified_at?: string | null;
  success_rate: number;
  avg_pollen_earned: number;
  success_count: number;
  fail_count: number;
  topic_tags: string[];
  export_version: string;
}

export interface SkillPublishChannel {
  id: string;
  label: string;
  description: string;
  action_url?: string | null;
  copy_text?: string | null;
}

export interface SkillPublishGuide {
  slug: string;
  suggested_price_eur_cents: number;
  suggested_price_display: string;
  github_repo_url: string;
  github_folder_path: string;
  gumroad_new_product_url: string;
  ballroom_mission_hint: string;
  install_command: string;
  channels: SkillPublishChannel[];
  checklist: string[];
}

export interface SkillExportResponse {
  meta: SkillExportMeta;
  files: SkillExportFile[];
  install_command: string;
  install_hint: string;
  publish?: SkillPublishGuide | null;
}

export interface SkillCatalogBuiltinItem {
  slug: string;
  title: string;
  version: string;
  roles: string[];
  keywords: string[];
  kind: "builtin";
}

export interface SkillCatalogRecipeItem {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  verified_at?: string | null;
  topic_tags: string[];
  success_rate: number;
  avg_pollen_earned: number;
  kind: "recipe";
  premium?: boolean;
  price_eur_cents?: number;
  unlocked?: boolean;
  ugc?: boolean;
  platform_cut_bps?: number | null;
}

export interface SkillMarketplaceConfigPayload {
  enabled: boolean;
  platform_cut_bps: number;
  platform_cut_display: string;
  price_tiers_cents: number[];
}

export interface SkillMarketplaceListingRow {
  id: string;
  recipe_id: string;
  recipe_name: string;
  status: string;
  price_eur_cents: number;
  platform_cut_bps: number;
  publisher_tenant_id: string;
  pitch?: string | null;
  curator_note?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
}

export interface LeadMagnetCatalogItem {
  template_id: string;
  name: string;
  tagline: string;
  description: string;
  estimated_minutes: number;
  time_saved_hours_per_week: number;
  accent_hex: string;
  agent_count: number;
  headline: string;
  landing_url: string;
  wizard_url: string;
}

export interface LeadMagnetShareChannel {
  id: string;
  label: string;
  text: string;
  char_count: number;
}

export interface LeadMagnetLandingResponse {
  template_id: string;
  name: string;
  headline: string;
  tagline: string;
  description: string;
  bullets: string[];
  estimated_minutes: number;
  time_saved_hours_per_week: number;
  accent_hex: string;
  agent_count: number;
  cta_label: string;
  cta_url: string;
  landing_url: string;
}

export interface LeadMagnetSharePackResponse extends LeadMagnetLandingResponse {
  verified_hours_saved?: number | null;
  hours_attribution_line: string;
  share_channels: LeadMagnetShareChannel[];
  share_card_markdown: string;
}

export interface SkillUnlockStatusResponse {
  stripe_checkout_ready: boolean;
  unlocked_recipe_ids: string[];
  premium_price_eur_cents_default: number;
}

export interface SkillCheckoutResponse {
  status: string;
  recipe_id: string;
  slug: string;
  purchase_id?: string | null;
  checkout_url?: string | null;
  amount_eur_cents?: string | null;
  message?: string | null;
}

export interface SkillConfirmCheckoutResponse {
  status: string;
  checkout_session_id?: string | null;
  recipe_id?: string | null;
  purchase_id?: string | null;
  payment_status?: string | null;
  message?: string | null;
}

export interface VerifiedPollenLeaderboardRow {
  rank: number;
  agent_id: string;
  agent_name: string;
  agent_role: string;
  swarm_id?: string | null;
  verified_pollen: number;
  total_pollen: number;
}

export interface BeeBadgeItem {
  id: string;
  label: string;
  description: string;
  tier: string;
  emoji: string;
}

export interface BeeBadgeProfile {
  agent_id: string;
  agent_name: string;
  agent_role: string;
  swarm_id?: string | null;
  verified_pollen: number;
  total_pollen: number;
  performance_pct: number;
  verified_task_count: number;
  badges: BeeBadgeItem[];
  badge_count: number;
}

export interface WhiteLabelConfig {
  brand_name?: string | null;
  logo_url?: string | null;
  accent_hex: string;
  hide_platform_branding: boolean;
  custom_domain?: string | null;
  custom_domain_status: string;
}

export interface EnterpriseComplianceConfig {
  data_retention_days: number;
  compliance_contact_email?: string | null;
  soc2_attestation_url?: string | null;
  monthly_audit_export: boolean;
  dedicated_hive_note?: string | null;
}

export interface HaProfileStatus {
  ha_mode_enabled: boolean;
  redis_failover_configured: boolean;
  postgres_replica_configured: boolean;
  backup_drill_script_available: boolean;
  profile_label: string;
  readiness_pct: number;
  dr_drill?: {
    report_available: boolean;
    last_drill_at: string | null;
    backup_duration_sec: number | null;
    restore_status: string | null;
    report_file: string | null;
    reports_dir: string | null;
  };
  ha_chaos?: {
    report_available: boolean;
    last_drill_at: string | null;
    passed: boolean | null;
    baseline_ready_code: number | null;
    degraded_ready_code: number | null;
    recovered_ready_code: number | null;
    expect_failover_ready: boolean;
    report_file: string | null;
    reports_dir: string | null;
  };
}

export interface EnterpriseWorkspaceView {
  tenant_id: string;
  tenant_name: string;
  white_label: WhiteLabelConfig;
  compliance: EnterpriseComplianceConfig;
  ha_profile: HaProfileStatus;
  custom_branding_allowed: boolean;
}

export interface PaperTradingFillRow {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  fill_price_usd: number;
  notional_usd: number;
  confidence: number;
  signal_note: string;
  created_at: string;
}

export interface PaperTradingProjectSnapshot {
  project_id: string;
  project_slug: string;
  display_name: string;
  mode: string;
  cash_usd: number;
  starting_cash_usd: number;
  equity_usd: number;
  realized_pnl_usd: number;
  daily_realized_pnl_usd: number;
  unrealized_pnl_usd: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  is_halted: boolean;
  halt_reason?: string | null;
  last_tick_at?: string | null;
  recent_fills?: PaperTradingFillRow[];
  disclaimer?: string;
}

export interface PaperTradingSummaryPayload {
  enabled: boolean;
  mode: string;
  project_count: number;
  total_equity_usd: number;
  total_pnl_usd: number;
  projects: PaperTradingProjectSnapshot[];
  disclaimer: string;
}

export type RapidLoopStageId = "scrape" | "reflect" | "simulate" | "reward";
export type RapidLoopStageStatus = "idle" | "active" | "ok" | "warn";

export interface RapidLoopStageRow {
  id: RapidLoopStageId;
  label: string;
  count_24h: number;
  last_at: string | null;
  status: RapidLoopStageStatus;
}

/** ``GET /api/v1/dashboard/rapid-loop`` — verified learning cycle telemetry. */
export interface RapidLoopSummaryPayload {
  generated_at: string;
  window_hours: number;
  sla_target_sec: number;
  sla_met_pct: number | null;
  avg_cycle_sec: number | null;
  last_cycle_sec: number | null;
  last_cycle_at: string | null;
  stages: RapidLoopStageRow[];
  loop_healthy: boolean;
  pattern_telemetry?: RapidLoopPatternTelemetryPayload | null;
}

export type TimeSavedSourceKind = "template" | "recipe" | "custom";

export interface TimeSavedBreakdownRow {
  source_key: string;
  source_kind: TimeSavedSourceKind;
  source_label: string;
  task_count: number;
  minutes_per_task: number;
  hours_saved: number;
}

/** ``GET /api/v1/dashboard/time-saved`` — verified workflow ROI estimates. */
export interface TimeSavedSummaryPayload {
  generated_at: string;
  window_days: number;
  verified_task_count: number;
  hours_saved_total: number;
  hours_saved_projected_monthly: number;
  minutes_per_task_default: number;
  breakdown: TimeSavedBreakdownRow[];
  disclaimer: string;
}

export interface UnifiedSavingsHeadline {
  total_value_usd: number;
  time_value_usd: number;
  llm_saved_usd: number;
  hours_saved_total: number;
  hours_saved_projected_monthly: number;
  llm_saved_pct: number | null;
  verified_task_count: number;
  llm_call_count: number;
}

export interface LlmCostSavingsPayload {
  window_days: number;
  call_count: number;
  actual_usd: number;
  quality_baseline_usd: number;
  saved_usd: number;
  saved_pct: number;
  routing_mode: string;
  cost_guardian_enabled: boolean;
}

/** ``GET /api/v1/dashboard/unified-savings`` — merged time + LLM savings. */
export interface UnifiedSavingsPayload {
  window_days: number;
  hourly_rate_usd: number;
  headline: UnifiedSavingsHeadline;
  time_saved: TimeSavedSummaryPayload;
  llm_savings: LlmCostSavingsPayload | null;
  llm_savings_available: boolean;
  disclaimer: string;
}

/** ``GET /api/v1/harness/pattern-explorer`` */
export interface PatternUsageRow {
  id: string;
  label: string;
  count: number;
}

export interface PatternCatalogRow {
  id: string;
  number: number;
  label: string;
  summary: string;
}

export interface PatternExplorerSessionRow {
  session_id: string;
  status: string;
  started_at: string | null;
  goal_preview: string;
  primary: string[];
  secondary: string[];
  all: string[];
  forced_reflection?: boolean;
  rationale: string[];
  router_version?: string;
}

export interface PatternExplorerPayload {
  window_hours: number;
  sessions_in_window: number;
  unique_patterns_today: number;
  router_enabled: boolean;
  forced_reflection_enabled: boolean;
  usage_today: PatternUsageRow[];
  catalog: PatternCatalogRow[];
  recent_sessions: PatternExplorerSessionRow[];
  docs_path: string;
}

export interface RapidLoopPatternTelemetryRow {
  id: string;
  label: string;
  sessions: number;
  success_count: number;
  failure_count: number;
  success_rate_pct: number | null;
}

export interface RapidLoopPatternTelemetryPayload {
  window_hours: number;
  sessions_analyzed: number;
  patterns_tracked: number;
  best_pattern: RapidLoopPatternTelemetryRow | null;
  top_patterns: RapidLoopPatternTelemetryRow[];
  catalog_size: number;
}

/** ``GET /api/v1/harness/snapshot`` */
export interface HarnessRuleLayerRow {
  id: string;
  path: string;
  scope: string;
  bytes: string;
}

export interface HarnessSkillRow {
  slug: string;
  title: string;
  priority: number;
  roles: string[];
  reference_mode?: boolean;
}

export interface HarnessPatternRow {
  session_id: string;
  status: string;
  started_at: string | null;
  primary: string[];
  secondary: string[];
  forced_reflection: boolean;
  rationale: string[];
}

export interface HarnessMonitoringPayload {
  slack_webhook_configured: boolean;
  alertmanager_receiver: string;
  pattern_alert_rules: string[];
  grafana_dashboard_uid: string;
  smoke_script: string;
  pattern_telemetry?: RapidLoopPatternTelemetryPayload;
}

export interface HarnessSnapshotPayload {
  rule_layers: HarnessRuleLayerRow[];
  skills: { count: number; reference_mode_count?: number; items: HarnessSkillRow[] };
  mcp_tools: { count: number; items: Record<string, unknown>[] };
  recent_agentic_patterns: HarnessPatternRow[];
  feature_flags: Record<string, boolean>;
  slack_trainer?: HarnessSlackTrainerStatus;
  lsp_bridge?: HarnessLspBridgeStatus;
  tech_health_score: number;
  monitoring: HarnessMonitoringPayload;
  docs: Record<string, string>;
}

export interface HarnessSlackTrainerStatus {
  enabled: boolean;
  signing_secret_configured: boolean;
  tenant_id_configured: boolean;
  slash_command_path: string;
}

export interface HarnessLspBridgeStatus {
  enabled: boolean;
  connector_slug: string;
  tools: string[];
  resolve_path: string;
}

/** ``POST /api/v1/harness/slack-trainer/feedback`` */
export interface SlackTrainerFeedbackResponse {
  tenant_id: string;
  kind: string;
  version: number;
  char_count: number;
  appended_chars: number;
  source: string;
  author?: string | null;
  slack_notified: boolean;
}

/** ``POST /api/v1/harness/intelligence-scan`` */
export interface HarnessIntelligenceProposal {
  kind: string;
  target: string;
  priority: string;
  rationale: string;
}

export interface HarnessIntelligenceScanPayload {
  scanned_at: string;
  proposal_count: number;
  proposals: HarnessIntelligenceProposal[];
}

export type PendingReviewStatus = "pending" | "approved" | "rejected";

export interface PendingReviewItemRow {
  id: string;
  task_id: string | null;
  swarm_id: string;
  workflow_id: string;
  simulation_id: string | null;
  status: PendingReviewStatus;
  reason: string;
  confidence_fraction: number | null;
  verification_passed: boolean;
  verification_notes: string | null;
  step_summary: Record<string, unknown> | null;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
}

export interface PendingReviewStats {
  pending_count: number;
  approved_count: number;
  rejected_count: number;
}

export interface SkillCatalogResponse {
  builtin: SkillCatalogBuiltinItem[];
  recipes: SkillCatalogRecipeItem[];
}

export interface HiveMdResponse {
  swarm_id: string;
  swarm_name: string;
  content: string;
  generated_at: string;
  extras: Record<string, unknown>;
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
  kanban_slice_count?: number | null;
}

/** Local hive mind summary embedded in swarm board/overview payloads. */
export interface SubSwarmLocalMindSummary {
  swarm_id: string;
  hive_sync_interval_sec: number;
  recommended_bee_count: number;
  needs_sync: boolean;
  last_sync_seconds_ago: number | null;
  sync_due_in_sec: number;
  sync_progress_pct: number;
  wizard_template?: string | null;
  swarm_role_label?: string | null;
  accent_hex?: string | null;
  last_waggle_cue?: string | null;
  goal_preview?: string | null;
  memory_key_count: number;
  peer_count: number;
}

export interface SubSwarmLocalMindDetail extends SubSwarmLocalMindSummary {
  local_memory_preview: Record<string, unknown>;
  member_count: number;
  is_active: boolean;
  purpose: string;
  slug: string;
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
  local_mind?: SubSwarmLocalMindSummary;
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

/** `/dashboard/swarms-overview` — Swarms page aggregate payload. */
export interface SwarmsOverviewColony {
  id: string;
  slug: string;
  display_name: string;
  lane: string;
  lane_label: string;
  queen_label: string;
  member_count: number;
  total_pollen: number;
  last_sync_seconds_ago: number | null;
  is_active: boolean;
  status: "active" | "paused";
  local_mind?: SubSwarmLocalMindSummary;
}

export interface SwarmsOverviewKpis {
  colonies_total: number;
  colonies_active: number;
  colonies_paused: number;
  total_bees: number;
  bees_working: number;
  bees_idle: number;
  pollen_pool: number;
  avg_sync_drift_sec: number;
  last_global_tick_sec: number | null;
}

export interface SwarmsHiveSyncRow {
  label: string;
  state: "synced" | "syncing";
  seconds_ago: number | null;
}

export interface SwarmsOverviewPayload {
  generated_at: string;
  hive_sync_interval_sec: number;
  kpis: SwarmsOverviewKpis;
  colonies: SwarmsOverviewColony[];
  waggle_feed: WaggleFeedItem[];
  hive_sync: SwarmsHiveSyncRow[];
}

/** `/dashboard/foragers-overview` — KPI tiles + configuration table. */
export interface ForagersOverviewConfiguration {
  id: string;
  source_name: string;
  source_type: string;
  schedule_label: string;
  last_run_seconds_ago: number | null;
  items_count: number;
  status: "ok" | "warn" | "paused" | "error";
  is_active: boolean;
}

export interface ForagersOverviewKpis {
  foragers_total: number;
  foragers_active: number;
  foragers_paused: number;
  foragers_error: number;
  items_ingested_24h: number;
  items_trend_pct: number | null;
  hivemind_chunks_7d: number;
  auto_spawned_bees: number;
}

export interface ForagersSpawnRule {
  id: string;
  forager_id: string;
  when_label: string;
  spawn_label: string;
  cooldown: string;
  enabled: boolean;
}

export interface ForagersOverviewPayload {
  generated_at: string;
  kpis: ForagersOverviewKpis;
  configurations: ForagersOverviewConfiguration[];
  spawn_rules: ForagersSpawnRule[];
}

export interface ForagerRow {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  source_type: string;
  source_config: Record<string, unknown>;
  filter_config: Record<string, unknown>;
  prompt_template: string;
  tools: string[];
  is_active: boolean;
  agent_template_id: string | null;
  supervisor_routine_id: string | null;
  created_at: string;
  updated_at: string;
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

/** `/dashboard/summary` — agent tier counts for operator panels. */
export interface DashboardSummaryPayload {
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

/** JWT list row from ``GET /api/v1/outputs`` (Phase 0.51 archive). */
export interface FinalDeliverableSummaryRow {
  id: string;
  lineage_id: string;
  version: number;
  title: string;
  slug: string;
  created_at: string;
  tags: string[];
  preview: string;
}

/** Full deliverable envelope including canonical Markdown — ``GET .../outputs/{id}``. */
export interface FinalDeliverableDetailRow extends FinalDeliverableSummaryRow {
  markdown_body: string;
  structured_json: Record<string, unknown>;
  voice_script: string | null;
  archive_relpath: string | null;
  chroma_embedding_id: string | null;
  ballroom_session_id: string | null;
  mission_id: string | null;
}

/** Semantic Chroma narrowed response — ``GET .../outputs/search``. */
export interface OutputsSearchResponse {
  items: FinalDeliverableSummaryRow[];
  query: string;
}
