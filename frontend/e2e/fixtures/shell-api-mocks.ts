import type { Page } from "@playwright/test";

import { resolvePlatformFeaturesFallback } from "../../lib/platform-features";
import { STUB_EXECUTION_STUDIO_OVERVIEW } from "./execution-studio-api-mocks";

const STUB_AGENT = {
  id: "a1111111-1111-4111-8111-111111111111",
  name: "Scout Bee",
  role: "scraper",
  status: "idle",
  pollen_points: 12,
  sub_swarm_id: "ss111111-1111-4111-8111-111111111111",
};

const STUB_SUMMARY = {
  generated_at: new Date().toISOString(),
  agents: { total: 1, by_status: { idle: 1 }, by_hive_tier: { worker: 1 } },
  tasks: { running: 0, pending: 0 },
  pollen_total: 12,
};

const STUB_ROUTINES = [
  {
    id: "r1111111-1111-4111-8111-111111111111",
    name: "Memory Dreaming",
    goal_template: "Run nightly memory consolidation and dream cycle synthesis.",
    schedule_kind: "interval",
    interval_seconds: 86_400,
    cron_expr: null,
    runtime_mode: "durable",
    roles: ["researcher", "critic"],
    retrieval_contract: "policy+last_3_tasks",
    skills: ["context", "diagnose"],
    context_payload: {},
    status: "scheduled",
    is_active: true,
    created_by_subject: "dash:test",
    last_run_at: new Date(Date.now() - 86_400_000).toISOString(),
    next_run_at: new Date().toISOString(),
    last_error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "r2222222-2222-4222-8222-222222222222",
    name: "Daily monitoring",
    goal_template: "Generate daily monitoring summary for operator review.",
    schedule_kind: "interval",
    interval_seconds: 3_600,
    cron_expr: null,
    runtime_mode: "durable",
    roles: ["researcher"],
    retrieval_contract: "policy",
    skills: ["context"],
    context_payload: {},
    status: "scheduled",
    is_active: true,
    created_by_subject: "dash:test",
    last_run_at: null,
    next_run_at: new Date().toISOString(),
    last_error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const STUB_TASK_QUEUE = {
  generated_at: new Date().toISOString(),
  tasks: [],
  pending_count: 0,
  running_count: 0,
  completed_today_count: 0,
};

const STUB_MISSION_KANBAN_TASK_ID = "22222222-2222-4222-8222-222222222222";

const STUB_MISSION_KANBAN_TASKS = [
  {
    id: STUB_MISSION_KANBAN_TASK_ID,
    title: "Content week",
    status: "completed",
    task_type: "agent_run",
    priority: 5,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    agent_name: null,
    payload: { task_text: "Launch content week for queenswarm.love (simulate-first)." },
  },
];

const STUB_COCKPIT_BUNDLE = {
  generated_at: new Date().toISOString(),
  revision: 1,
  agents: [STUB_AGENT],
  recent_tasks: [],
  summary: STUB_SUMMARY,
  system_status: {
    agents_total: 1,
    agents_running: 0,
    tasks_running: 0,
    tasks_pending: 0,
    llm_grok: true,
    llm_anthropic: false,
  },
};

const STUB_OPERATOR_COCKPIT = {
  enabled: true,
  generated_at: new Date().toISOString(),
  now_actions: [
    {
      id: "start_day",
      label: "Start day",
      detail: "Trio cycle + morning brief pipeline (verify-first).",
      priority: "high",
      href: null,
      action: "start_day",
    },
  ],
  swarm_fleet: [],
  trio: { lanes_bound: 3, bound_lane_count: 3 },
  oracle_warnings: [],
  feature_modules: [],
  innovation_lab: { enabled: true, pending_count: 0 },
  intent_crystallizer: { enabled: true, min_chars: 8, templates: [] },
  icm_tools: {
    enabled: true,
    link_drop_enabled: true,
    dialogue_extract_enabled: true,
    keyword_scan_enabled: true,
    min_dialogue_chars: 40,
    min_url_chars: 8,
    quick_automations: [
      { id: "morning_check", label: "Morning check", detail: "Trio cycle", kind: "action", action: "start_day", href: null },
    ],
  },
  links: { cockpit: "/agentic-os" },
};

const STUB_FOUR_CS_AUDIT = {
  overall_score: 72,
  overall_status: "ok",
  dimensions: [
    {
      id: "context",
      label: "Context",
      score: 70,
      status: "ok",
      signals: ["Curated instructions ~400 chars", "Wiki Layer enabled"],
      actions: [],
    },
    {
      id: "connections",
      label: "Connections",
      score: 65,
      status: "warn",
      signals: ["3 MCP tools registered", "Supervisor routines enabled"],
      actions: ["Enable routine webhooks (L4)"],
    },
    {
      id: "capabilities",
      label: "Capabilities",
      score: 80,
      status: "ok",
      signals: ["12 harness skills", "Queen Maintainer (PR-only)"],
      actions: [],
    },
    {
      id: "cadence",
      label: "Cadence",
      score: 55,
      status: "warn",
      signals: ["Maintainer runs today 0/3"],
      actions: ["Schedule a verified recipe as routine"],
    },
  ],
  maintainer_safety: [
    { id: "force_push", label: "No git push --force" },
    { id: "deploy_prod", label: "No direct deploy-prod / prod compose" },
  ],
};

const STUB_INJECTION_GUARD_COVERAGE = {
  enabled: true,
  status: "healthy",
  total_scans: 42,
  total_blocked: 1,
  guarded_tool_count: 7,
  checkpoints: [
    {
      checkpoint_id: "operator_input",
      label: "Operator input",
      scans: 10,
      blocked: 0,
      block_rate_pct: 0,
      coverage_pct: 100,
    },
    {
      checkpoint_id: "external_tool",
      label: "External tool",
      scans: 28,
      blocked: 1,
      block_rate_pct: 3.57,
      coverage_pct: 100,
    },
    {
      checkpoint_id: "agent_output",
      label: "Agent output",
      scans: 4,
      blocked: 0,
      block_rate_pct: 0,
      coverage_pct: 100,
    },
  ],
  tools: [
    {
      tool_name: "web_search",
      label: "Web search",
      scans: 12,
      blocked: 1,
      covered: true,
      checkpoint_id: "external_tool",
    },
  ],
  recent_hits: [
    {
      at: "2026-06-05T10:00:00.000Z",
      checkpoint_id: "external_tool",
      checkpoint_label: "External tool",
      tool_name: "web_search",
      matched_pattern: "ignore\\s+previous",
    },
  ],
  operator_hint: "Guard coverage active — external tools and session outputs scanned at all three checkpoints.",
  updated_at: "2026-06-05T10:00:00.000Z",
};

const STUB_INNOVATION_VIABILITY = {
  ok: true,
  status: "pass",
  checks: [
    { id: "innovation_lab", label: "Innovation Lab", status: "pass", detail: "Enabled" },
    { id: "maintainer", label: "Queen Maintainer", status: "pass", detail: "Enabled (PR-only)" },
    { id: "approved", label: "Operator approval", status: "pass", detail: "Approved" },
    { id: "plan", label: "Implementation plan", status: "pass", detail: "Plan present" },
  ],
  blocked_reasons: [],
};

const STUB_INNOVATION_LAB = {
  enabled: true,
  proposals: [
    {
      id: "00000000-0000-4000-8000-000000000099",
      title: "Innovation: E2E viability smoke",
      status: "pending",
      risk_level: "medium",
      feature_modules: ["hive_innovation_lab"],
      implementation_plan_md: "# Plan\n".repeat(20),
    },
  ],
};

const STUB_RAPID_LOOP = {
  generated_at: new Date().toISOString(),
  window_hours: 24,
  sla_target_sec: 60,
  sla_met_pct: 100,
  avg_cycle_sec: 12,
  last_cycle_sec: 8,
  last_cycle_at: new Date().toISOString(),
  loop_healthy: true,
  stages: [
    { id: "scrape", label: "Scrape", count_24h: 0, last_at: null, status: "idle" },
    { id: "reflect", label: "Reflect", count_24h: 0, last_at: null, status: "idle" },
    { id: "simulate", label: "Simulate", count_24h: 0, last_at: null, status: "idle" },
    { id: "reward", label: "Reward", count_24h: 0, last_at: null, status: "idle" },
  ],
};

const STUB_TIME_SAVED = {
  generated_at: new Date().toISOString(),
  window_days: 30,
  verified_task_count: 0,
  hours_saved_total: 0,
  hours_saved_projected_monthly: 0,
  breakdown: [],
  disclaimer: "Stub ROI estimates for shell E2E.",
};

const STUB_LLM_ROUTING_SETTINGS = {
  routing_mode: "free_first",
  cost_guardian_enabled: true,
  auto_upgrade_on_failure: true,
  feature_enabled: true,
  quality_primary_model: "grok-3",
  economy_primary_model: "gpt-4o-mini",
  local_llm_enabled: true,
  llm_airgap: false,
  ollama_default_model: "ollama/qwen2.5:7b",
  configured_local_models: ["ollama/qwen2.5:7b"],
};

const STUB_LOCAL_INFERENCE = {
  enabled: true,
  llm_airgap: false,
  ollama_api_base: "http://127.0.0.1:11434",
  ollama_default_model: "ollama/qwen2.5:7b",
  vllm_api_base: "",
  vllm_default_model: "openai/local-model",
  configured_models: ["ollama/qwen2.5:7b"],
  pings: [],
};

const STUB_LLM_COST_SAVINGS = {
  window_days: 30,
  call_count: 42,
  actual_usd: 1.25,
  quality_baseline_usd: 4.8,
  saved_usd: 3.55,
  saved_pct: 73.96,
  routing_mode: "free_first",
  cost_guardian_enabled: true,
};

const STUB_UNIFIED_SAVINGS = {
  window_days: 30,
  hourly_rate_usd: 50,
  headline: {
    total_value_usd: 503.5,
    time_value_usd: 500,
    llm_saved_usd: 3.55,
    hours_saved_total: 10,
    hours_saved_projected_monthly: 12,
    llm_saved_pct: 73.96,
    verified_task_count: 4,
    llm_call_count: 42,
  },
  time_saved: STUB_TIME_SAVED,
  llm_savings: STUB_LLM_COST_SAVINGS,
  llm_savings_available: true,
  disclaimer: "Stub unified savings for shell E2E.",
};

const STUB_HARNESS_SNAPSHOT = {
  rule_layers: [{ id: "cursorrules", path: ".cursorrules", scope: "root", bytes: "2048" }],
  skills: { count: 3, reference_mode_count: 1, items: [{ slug: "self-review-loop", title: "Self Review", priority: 10, roles: [], reference_mode: true }] },
  mcp_tools: { count: 0, items: [] },
  recent_agentic_patterns: [],
  feature_flags: {
    supervisor_pattern_router_enabled: true,
    supervisor_forced_reflection_enabled: true,
    supervisor_pattern_router_llm_enabled: false,
    skill_lazy_reference_fetch_enabled: true,
    slack_harness_trainer_enabled: true,
    lsp_mcp_bridge_enabled: false,
    rubric_templates_enabled: true,
    forager_intelligence_loop_enabled: false,
  },
  slack_trainer: {
    enabled: true,
    signing_secret_configured: false,
    tenant_id_configured: false,
    slash_command_path: "/api/v1/harness/slack-trainer/slack-command",
  },
  lsp_bridge: {
    enabled: false,
    connector_slug: "queenswarm_lsp",
    tools: ["resolve_symbol", "list_file_symbols", "find_references"],
    resolve_path: "/api/v1/harness/lsp-bridge/resolve",
  },
  rubric_templates: {
    enabled: true,
    count: 5,
    list_path: "/api/v1/harness/rubric-templates",
  },
  forager_intelligence: {
    enabled: false,
    celery_task: "hive.forager_intelligence_daily_tick",
    cron_utc: "06:00",
    cron_hour: 6,
    cron_minute: 0,
    manual_scan_path: "/api/v1/harness/intelligence-scan",
  },
  queen_maintainer: {
    enabled: false,
    post_merge_webhook: {
      enabled: false,
      secret_configured: false,
      tenant_id_configured: false,
      github_owner: "",
      github_repo: "",
      webhook_path: "/api/v1/queen-maintainer/github-webhook",
      accepted_events: ["ping", "pull_request", "push"],
    },
    tech_health_path: "/api/v1/queen-maintainer/tech-health",
  },
  tech_health_score: 0.85,
  monitoring: {
    slack_webhook_configured: false,
    alertmanager_receiver: "blackhole",
    pattern_alert_rules: ["PatternSuccessRateLow"],
    grafana_dashboard_uid: "queenswarm-agentic-patterns",
    smoke_script: "scripts/alertmanager-smoke.sh",
  },
  docs: {},
};

const STUB_HARNESS_INTELLIGENCE_SCAN = {
  scanned_at: new Date().toISOString(),
  proposal_count: 0,
  proposals: [],
};

const STUB_PATTERN_EXPLORER = {
  router_enabled: true,
  forced_reflection_enabled: true,
  window_hours: 24,
  sessions_in_window: 0,
  unique_patterns_today: 0,
  usage_today: [],
  catalog: [{ id: "planning", number: 6, label: "Planning", summary: "Orchestration" }],
  recent_sessions: [],
  docs_path: "docs/QUEENSWARM_DESIGN_PATTERNS.md",
};

const STUB_EPISODIC_SUMMARY = {
  retention_days: 90,
  counts: {
    session_events: 2,
    dream_insights: 1,
    dump_sleep_batches: 0,
    session_summaries: 1,
  },
  total_items: 4,
  latest_at: "2026-05-21T08:00:00.000Z",
};

const STUB_EPISODIC_TIMELINE = {
  retention_days: 90,
  item_count: 1,
  items: [
    {
      id: "evt-stub-1",
      kind: "session_event",
      occurred_at: "2026-05-21T08:00:00.000Z",
      title: "Session started",
      summary: "Supervisor session created.",
      session_id: null,
      metadata: {},
    },
  ],
};

const STUB_EPISODIC_DAILY_LOG = {
  enabled: true,
  retention_days: 90,
  total_captures: 1,
  operator_hint: "Completed supervisor sessions auto-capture into the daily episodic log.",
  days: [
    {
      date: "2026-05-21",
      session_count: 1,
      headline: "Gumroad hero pack",
      summary_md: "Listing draft with CTA ready for operator approve.",
      captures: [
        {
          capture_id: "capture:stub-1",
          session_id: "00000000-0000-4000-8000-000000000001",
          captured_at: "2026-05-21T08:00:00.000Z",
          day: "2026-05-21",
          goal: "Gumroad hero pack",
          summary: "Listing draft with CTA ready for operator approve.",
          status: "completed",
          rubric_score: null,
          href: "/agents?session=stub-1",
        },
      ],
    },
  ],
};

const STUB_COST_SUMMARY = {
  window_days: 35,
  series: [{ day: new Date().toISOString().slice(0, 10), spend_usd: 1.25, model: "grok" }],
};

const STUB_FORAGERS_OVERVIEW = {
  policy: { auto_spawn_auto_approve_enabled: false },
  kpis: {
    foragers_total: 0,
    foragers_paused: 0,
    foragers_error: 0,
    items_ingested_24h: 0,
    hivemind_chunks_7d: 0,
    items_trend_pct: null,
  },
  configurations: [],
};

const STUB_FORAGER_GOLDMINE_ALERTS = {
  enabled: true,
  alerts: [],
  operator_hint: "Dispatch attaches a skill bundle and parks triage on Mission Kanban.",
};

const STUB_DATA_MONITOR_WIZARD = {
  enabled: true,
  min_intent_chars: 12,
  examples: [
    {
      intent: "Track senior Python remote jobs in EU on public job boards",
      niche: "jobs",
      label: "EU Python jobs",
    },
  ],
  niches: [
    {
      id: "jobs",
      label: "Jobs & hiring",
      description: "Job boards and hiring pages.",
      extract_schema: "jobs",
    },
  ],
  schedule_presets: ["6h", "12h", "24h", "daily_6utc"],
  operator_hint: "One sentence → scheduled forager with schema.",
};

const STUB_DATA_MONITOR_PLAN = {
  niche: "jobs",
  niche_label: "Jobs & hiring",
  source_type: "rss",
  forager_name: "Monitor · Jobs & hiring · Track senior Python…",
  description: "Track senior Python remote jobs in EU on public job boards",
  extract_schema: "jobs",
  topic_tags: ["jobs", "monitor", "goldmine"],
  skill_bundle: ["competitor-scrape-analyze", "context", "research"],
  schedule_label: "every 24h",
  interval_seconds: 86400,
  source_config_summary: "Add RSS feed URLs in Edit after create",
  prompt_template: "Extract employer, role title, location.",
};

const STUB_FORAGER_DISCOVERY_WIZARD = {
  enabled: true,
  keys_configured: true,
  tavily_configured: true,
  serper_configured: true,
  max_urls: 8,
  operator_hint: "Discover public URLs via Serper/Tavily.",
};

const STUB_FORAGER_DISCOVERY_SEARCH = {
  enabled: true,
  query: "EU python job board RSS",
  hits: [
    {
      url: "https://jobs.example.com/feed.xml",
      title: "Example jobs feed",
      snippet: "Open roles in EU",
      provider: "serper",
      url_kind: "rss",
    },
  ],
  providers_used: ["serper"],
  keys_configured: true,
  operator_hint: "Select URLs and bind.",
};

const STUB_OPERATOR_APPROVALS = {
  enabled: true,
  generated_at: "2026-06-05T10:00:00Z",
  counts: {
    publish_queue: 0,
    agent_suggestions: 0,
    lane_digests: 0,
    innovation: 0,
    gumroad_manual: 0,
    goldmine_alerts: 1,
    total: 1,
  },
  items: [
    {
      id: "goldmine:e2e-forager-goldmine-1",
      kind: "goldmine_alert",
      lane: "intel",
      title: "Goldmine · E2E YouTube Intel · 3 new",
      detail: "3 new signals since last run · Spawn rules: High fit",
      created_at: null,
      href: "/foragers",
      source_id: "e2e-forager-goldmine-1",
      reject_supported: false,
    },
  ],
};

const STUB_PLATFORM_FEATURES = {
  ...resolvePlatformFeaturesFallback({
    platformMode: "commercial",
    isAdmin: true,
    subscriptionTier: "free",
  }),
  /** E2E: enterprise settings route + cross-links (commercial free tier otherwise blocks). */
  enterprise_workspace: true,
  /** E2E: legacy `/external-projects` → integrations external tab must stay addressable. */
  external_projects: true,
  connectors: true,
  plugins: true,
  /** E2E: `/factory` blueprint lane (commercial profile otherwise blocks route). */
  skills_export_factory: true,
  /** E2E: `/foragers` More-menu route (pro tier otherwise blocks). */
  foragers: true,
  /** E2E: `/jobs` async poll console (internal-only feature on commercial). */
  jobs: true,
  /** E2E: integrations Execution Studio tab (`?tab=studio`). */
  execution_studio: true,
  /** E2E: Ballroom Dump & Sleep panel (pro tier otherwise blocks). */
  dump_sleep: true,
  /** E2E: Settings → Harness AI layer dashboard. */
  ai_harness_dashboard: true,
};

const STUB_ENTERPRISE_CONFIG = {
  tenant_id: "00000000-0000-4000-8000-000000000001",
  tenant_name: "Playwright Hive",
  white_label: {
    brand_name: "QueenSwarm",
    logo_url: null,
    accent_hex: "#FFB800",
    hide_platform_branding: false,
    custom_domain: null,
    custom_domain_status: "pending",
  },
  compliance: {
    data_retention_days: 365,
    compliance_contact_email: "compliance@queenswarm.love",
    soc2_attestation_url: null,
    monthly_audit_export: false,
    dedicated_hive_note: null,
  },
  ha_profile: {
    ha_mode_enabled: false,
    redis_failover_configured: false,
    postgres_replica_configured: false,
    backup_drill_script_available: true,
    profile_label: "Standard hive",
    readiness_pct: 72,
  },
  custom_branding_allowed: true,
};

const STUB_OPERATOR_ME = {
  id: "dash:00000000-0000-4000-8000-000000000001",
  email: "operator@queenswarm.love",
  display_name: "Playwright Operator",
  twofa_enabled: false,
  twofa_pending: false,
  backup_codes_remaining: 0,
  is_admin: true,
  single_admin_mode: false,
  platform_mode: "commercial",
  subscription_tier: "free",
  solo_mode: true,
  platform_features: STUB_PLATFORM_FEATURES,
  scopes: ["dash:admin", "dash:operator", "dash:read"],
};

export const STUB_AGENT_ID = STUB_AGENT.id;

const STUB_BILLING_USAGE = {
  tenant_id: "00000000-0000-4000-8000-000000000001",
  tier: "free",
  status: "active",
  billing_customer_id: null,
  billing_subscription_id: null,
  usage: {
    monthly_tokens: 1200,
    monthly_supervisor_sessions: 2,
    monthly_external_calls: 0,
    storage_mb_estimate: 12.5,
    monthly_spend_usd: 0.42,
  },
  limits: {
    monthly_tokens_hard: 100000,
    monthly_supervisor_sessions_hard: 50,
    monthly_external_calls_hard: 500,
    storage_mb_hard: 512,
  },
  usage_health: {},
  features: {},
  upgrade_recommended: false,
};

const STUB_BILLING_PLANS = {
  current_tier: "free",
  checkout_ready: false,
  message: "stub",
  pro_price_eur_cents: 2900,
  enterprise_price_eur_cents: 9900,
  plans: [
    {
      tier: "free",
      label: "Free hive",
      limits: {
        monthly_tokens_hard: 100000,
        monthly_supervisor_sessions_hard: 50,
        monthly_external_calls_hard: 500,
        max_agents_hard: 10,
        max_swarms_hard: 3,
        storage_mb_hard: 512,
      },
      features: { ballroom: true },
    },
    {
      tier: "pro",
      label: "Pro hive",
      limits: {
        monthly_tokens_hard: 500000,
        monthly_supervisor_sessions_hard: 200,
        monthly_external_calls_hard: 2000,
        max_agents_hard: 50,
        max_swarms_hard: 10,
        storage_mb_hard: 2048,
      },
      features: { ballroom: true, premium_recipes: true },
    },
    {
      tier: "enterprise",
      label: "Enterprise hive",
      limits: {
        monthly_tokens_hard: 2000000,
        monthly_supervisor_sessions_hard: 1000,
        monthly_external_calls_hard: 10000,
        max_agents_hard: 200,
        max_swarms_hard: 50,
        storage_mb_hard: 10240,
      },
      features: { ballroom: true, premium_recipes: true, admin_accounts: true },
    },
  ],
};

const STUB_SKILLS_CATALOG = {
  builtin: [
    {
      slug: "grill-me",
      title: "Grill me",
      version: "1.0.0",
      keywords: ["review", "critique"],
      roles: ["supervisor"],
    },
  ],
  recipes: [
    {
      id: "r1111111-1111-4111-8111-111111111111",
      name: "Verified workflow export",
      slug: "verified-workflow-export",
      description: "Stub premium recipe for shell E2E.",
      verified_at: new Date().toISOString(),
      topic_tags: ["premium"],
      success_rate: 0.92,
      avg_pollen_earned: 8,
      kind: "recipe",
      premium: true,
      price_eur_cents: 1900,
      unlocked: false,
    },
  ],
};

const STUB_SKILL_UNLOCKS = {
  checkout_available: false,
  unlocked_recipe_ids: [] as string[],
  premium_price_eur_cents_default: 1900,
};

const STUB_RECIPES_CATALOG = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    name: "Lead Gen Lane",
    description: "ICP to outreach drafts",
    verified_at: new Date().toISOString(),
    topic_tags: ["lead", "outreach"],
    pattern_labels: ["planning"],
    success_count: 12,
    fail_count: 1,
    avg_pollen_earned: 42,
  },
];

const STUB_RECIPE_MATCH_CONFIG = {
  match_threshold: 0.85,
  min_search_similarity: 0.5,
  hybrid_scoring_enabled: true,
  hybrid_vector_weight: 0.7,
  hybrid_graph_weight: 0.3,
};

const STUB_MISSION_KANBAN_RECIPE_MATCH = {
  enabled: true,
  query: "Ship Gumroad hero pack listing draft",
  match_config: STUB_RECIPE_MATCH_CONFIG,
  operator_hint: "Pick a verified recipe to bind workflow decomposition on dispatch.",
  hits: [
    {
      chroma_document_id: "recipe-hit-stub-1",
      similarity: 0.91,
      vector_similarity: 0.91,
      graph_score: 0.72,
      document_preview: "Verified Gumroad listing workflow with CTA checklist.",
      postgres_recipe_id: "11111111-1111-4111-8111-111111111111",
      postgres_row: STUB_RECIPES_CATALOG[0],
    },
  ],
};

const STUB_FACTORY_LLM_READINESS = {
  grok_configured: false,
  anthropic_configured: false,
  openai_configured: false,
  openrouter_configured: true,
  chain_usable: true,
  build_allowed: true,
  grok_primary: false,
  openrouter_primary: true,
  primary_model: "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
  recommended_action:
    "Nemotron/OpenRouter ready (openrouter/nvidia/nemotron-3-ultra-550b-a55b:free) — run smoke test, then start factory builds.",
  decomposition_chain: ["openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"],
  available_models: [
    {
      value: "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
      label: "Nemotron 3 Ultra (OpenRouter · free)",
      configured: true,
    },
    {
      value: "xai/grok-3-mini",
      label: "Grok 3 Mini (xAI)",
      configured: false,
    },
  ],
  smoke_ok: null,
  smoke_error: null,
};

const STUB_SKILL_FACTORY_SNAPSHOT = {
  policy: {
    enabled: true,
    niche_seeds: ["indie hacker SEO blog pipeline"],
    auto_build_enabled: false,
    auto_build_min_score: 0.72,
    max_builds_per_week: 5,
    research_cron_enabled: false,
    apify_deep_scrape_enabled: false,
    monid_listing_signals_enabled: false,
    monid_listing_preview_on_approve: false,
    monid_listing_video_preview_on_approve: false,
  },
  opportunities: [],
  queue_count: 0,
  building_count: 0,
  failed_count: 0,
  actionable_count: 0,
  opportunity_counts: {
    pending: 0,
    queued: 0,
    building: 0,
    awaiting_forge: 0,
    failed: 0,
    completed: 0,
    dismissed: 0,
    total: 0,
    actionable: 0,
  },
  opportunities_truncated: false,
  library_count: 0,
  sellable_count: 0,
  research_keys_configured: false,
  llm: STUB_FACTORY_LLM_READINESS,
  queue_slo: {
    enabled: true,
    status: "healthy",
    awaiting_forge: 0,
    awaiting_forge_warn: 3,
    awaiting_forge_critical: 8,
    critic_approval_rate: null,
    critic_samples: 0,
    weekly_builds_used: 0,
    weekly_build_cap: 5,
    weekly_cap_pct: 0,
    alerts: [],
    next_operator_action: "Queue healthy — no action required.",
  },
};

const STUB_APPS_TOOLS_INDEX = {
  generated_at: new Date().toISOString(),
  version: "v1",
  workspaces: [
    {
      module_key: "marketing_automation",
      label: "Marketing Automation",
      layer: "apps_tools",
      summary: "Campaign publishing and distribution workflows.",
      status: "live",
      enabled: true,
      capability_keys: ["apps.marketing.publish_pipeline.v1"],
    },
  ],
  capabilities: [
    {
      capability_key: "apps.marketing.publish_pipeline.v1",
      label: "Marketing publish pipeline",
      owner_module: "marketing_automation",
      surface: "apps_tools",
      summary: "Generate and orchestrate multi-channel publish packs.",
      status: "live",
      version: "v1",
      risk_tier: "publish",
      requires_approval: true,
      input_schema_ref: "schemas/apps.marketing.publish_pipeline.input.v1.json",
      output_schema_ref: "schemas/apps.marketing.publish_pipeline.output.v1.json",
      enabled: true,
      sla_hint_sec: 180,
      dependency_keys: ["integrations.connector.invoke.v1"],
      tags: ["apps", "marketing", "publish"],
    },
  ],
  policies: [
    {
      module_key: "marketing_automation",
      label: "Marketing Automation",
      enabled: true,
      risk_tier: "publish",
      requires_approval: true,
      cooldown_sec: null,
      spend_cap_usd_24h: 10,
      time_limit_sec: 12,
      rate_limit_window_sec: 86400,
      rate_limit_max_global: 30,
      notes: ["Live publish is simulation-first."],
    },
  ],
};

const STUB_APPS_TOOLS_ANALYTICS = {
  window: "24h",
  compact_mode: false,
  last_event_at: new Date().toISOString(),
  total_events: 0,
  counters: {},
  module_funnel: [],
  top_movers: [],
  recommendation: null,
};

const STUB_RECIPE_PATTERN_STACKS = [
  {
    id: "exec_assistant",
    label: "Exec Assistant",
    pattern_tags: ["planning", "rag", "reflection", "goal_monitoring"],
    pattern_labels: ["Planning", "RAG", "Reflection", "Goal Monitoring"],
  },
  {
    id: "life_os",
    label: "Life OS",
    pattern_tags: ["memory_management", "prioritization", "reflection", "planning"],
    pattern_labels: ["Memory", "Prioritization", "Reflection", "Planning"],
  },
];

const STUB_SWARMS_OVERVIEW = {
  generated_at: new Date().toISOString(),
  hive_sync_interval_sec: 300,
  kpis: {
    colonies_total: 0,
    colonies_active: 0,
    colonies_paused: 0,
    total_bees: 0,
    bees_working: 0,
    bees_idle: 0,
    pollen_pool: 0,
    avg_sync_drift_sec: 0,
    last_global_tick_sec: null,
  },
  colonies: [],
  waggle_feed: [],
  hive_sync: [],
};

const STUB_SWARM_BOARD = {
  sub_swarms: [],
  waggle_feed: [],
  generated_at: new Date().toISOString(),
};

const STUB_HIVE_GRAPH = {
  nodes: [],
  edges: [],
  generated_at: new Date().toISOString(),
};

const STUB_PROJECT_SHAPE = {
  shape: "project",
  tenant_id: "00000000-0000-4000-8000-000000000001",
  nodes: [
    {
      id: "gb:batch-1",
      graph_kind: "GraphifyBatch",
      label: "Research dump",
      summary: "2 files ingested",
      tags: ["auto_graphify"],
    },
    {
      id: "vf:graphify/demo/batch",
      graph_kind: "VaultFolder",
      label: "Research dump",
      summary: "graphify/demo/batch",
      rel_path: "graphify/demo/batch",
    },
    {
      id: "doc-hash-1",
      graph_kind: "VaultDocument",
      label: "notes.md",
      summary: "Priority queue notes",
      rel_path: "notes.md",
      tags: ["auto_graphify"],
    },
  ],
  edges: [
    { source: "gb:batch-1", target: "vf:graphify/demo/batch", kind: "ROOTED_IN" },
    { source: "vf:graphify/demo/batch", target: "doc-hash-1", kind: "CONTAINS" },
  ],
};

const STUB_PAPER_TRADING = {
  enabled: false,
  positions: [],
  summary: { pnl_usd: 0, trades_total: 0 },
};

const STUB_AUTONOMY_SUMMARY = {
  tenant_id: "00000000-0000-4000-8000-000000000001",
  autonomy_mode: "supervised",
  active_long_horizon_routines: 0,
  pending_memory_approvals: 0,
  pending_initiative_approvals: 0,
  average_strategy_score: 0.62,
  reflection_entries: 0,
  status: "idle",
};

const STUB_PREVIEW_DECOMPOSITION = {
  steps: [
    {
      step_order: 1,
      description: "Research market context",
      agent_role: "scraper",
      guardrails: {},
      evaluation_criteria: {},
      guardrail_summary: "Read-only sources",
    },
    {
      step_order: 2,
      description: "Evaluate findings",
      agent_role: "evaluator",
      guardrails: {},
      evaluation_criteria: {},
      guardrail_summary: "Score confidence",
    },
    {
      step_order: 3,
      description: "Draft operator report",
      agent_role: "reporter",
      guardrails: {},
      evaluation_criteria: {},
      guardrail_summary: "Verified output only",
    },
  ],
  decomposition_rationale: "Stub decomposition for shell E2E.",
  recipe_match: null,
};

/**
 * Install API mocks for local Playwright webserver runs only.
 *
 * Remote hive smoke (``PLAYWRIGHT_BASE_URL``) skips mocks so the real edge + proxy path is exercised.
 */
export async function maybeInstallShellApiMocks(page: Page): Promise<void> {
  if (process.env.PLAYWRIGHT_BASE_URL) {
    return;
  }
  await installShellApiMocks(page);
}

/**
 * Stubs common proxy routes so authenticated shell E2E runs without a live hive backend.
 *
 * Server Components still SSR without backend — pages degrade gracefully with empty initial data.
 */
export async function installShellApiMocks(page: Page): Promise<void> {
  await page.route("**/api/proxy/**", async (route) => {
    const url = route.request().url();
    const path = new URL(url).pathname.replace(/^\/api\/proxy\/?/, "");

    if (path.startsWith("dashboard/cockpit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_COCKPIT_BUNDLE),
      });
      return;
    }

    if (path === "operator/cockpit" || path.startsWith("operator/cockpit?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_OPERATOR_COCKPIT),
      });
      return;
    }

    if (path === "operator/approvals" || path.startsWith("operator/approvals?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_OPERATOR_APPROVALS),
      });
      return;
    }

    if (path === "operator/business/snapshot") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          generated_at: new Date().toISOString(),
          headline: "First Gumroad upload",
          tagline: "Verified skills and revenue — simulate-first, sell with confidence.",
          catalog: { product_count: 14, featured_count: 3, gumroad_linked_count: 0, marketing_origin: "https://letagentscook.org" },
          catalog_wave: {
            current_wave: "wave_1",
            target_next: 25,
            mk6_target: 50,
            scorecard_clean_count: 14,
            catalog_deduped_count: 14,
            gap_to_next_wave: 11,
            gap_to_mk6: 36,
            seed_pending_count: 52,
            next_operator_action: "Run Skill + Content Pack Factory on pending seeds",
          },
          revenue: { ready_summary: "Ready: **14/16**", scorecard_ready_count: 14, first_upload_candidate: "`hero-pack`", next_operator_action: "Upload first listing" },
          missions: { triage_count: 0, ready_count: 0, in_progress_count: 0, blocked_count: 0 },
          top_actions: [
            { id: "gumroad_first_upload", lane: "revenue", title: "First Gumroad upload", detail: "Upload from queue", priority: "high", href: "/factory" },
          ],
          simulation_pass_rate: {
            enabled: true,
            status: "healthy",
            trend: "up",
            pass_rate_7d_pct: 85.0,
            pass_rate_30d_pct: 78.5,
            total_7d: 20,
            passed_7d: 17,
            failed_7d: 2,
            inconclusive_7d: 1,
            gate_threshold_pct: 70,
            operator_hint: "Verify-first gate at 70% — 17/20 simulations passed in 7 days.",
            daily: [
              { date: "2026-05-30", total: 2, passed: 2, pass_rate_pct: 100 },
              { date: "2026-05-31", total: 3, passed: 2, pass_rate_pct: 66.67 },
              { date: "2026-06-01", total: 4, passed: 3, pass_rate_pct: 75 },
              { date: "2026-06-02", total: 3, passed: 3, pass_rate_pct: 100 },
              { date: "2026-06-03", total: 2, passed: 2, pass_rate_pct: 100 },
              { date: "2026-06-04", total: 4, passed: 3, pass_rate_pct: 75 },
              { date: "2026-06-05", total: 2, passed: 2, pass_rate_pct: 100 },
            ],
          },
          links: { marketing_skills: "https://letagentscook.org/skills", mission_control: "/tasks", factory: "/factory" },
        }),
      });
      return;
    }

    if (path === "operator/innovation-lab" || path.startsWith("operator/innovation-lab?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_INNOVATION_LAB),
      });
      return;
    }

    if (path.includes("operator/innovation-lab/proposals/") && path.endsWith("/viability")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_INNOVATION_VIABILITY),
      });
      return;
    }

    if (path === "harness/four-cs-audit" || path.startsWith("harness/four-cs-audit?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FOUR_CS_AUDIT),
      });
      return;
    }

    if (path === "harness/injection-guard-coverage" || path.startsWith("harness/injection-guard-coverage?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_INJECTION_GUARD_COVERAGE),
      });
      return;
    }

    if (path === "operator/link-drop") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          brief: { title: "Stub brief", summary: "E2E stub", enabled: true },
        }),
      });
      return;
    }

    if (path.startsWith("operator/ballroom/") && path.endsWith("/transcript-text")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          text: "User: Can you tighten our onboarding copy for next week?\nAssistant: Here is a shorter draft with clearer CTAs.",
          char_count: 120,
        }),
      });
      return;
    }

    if (path.startsWith("operator/dump-sleep/") && path.endsWith("/transcript-text")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          text: "User: Voice note about launch deadline.\n\nOvernight briefing:\n- Must ship onboarding by Friday.",
          char_count: 90,
        }),
      });
      return;
    }

    if (path === "operator/dialogue-extract" || path === "operator/keyword-scan") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          extraction: { summary_md: "## Stub", goals: ["Test"], task_prefill: "Test goal" },
          scan: { matches: [] },
        }),
      });
      return;
    }

    if (path.startsWith("dashboard/rapid-loop")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_RAPID_LOOP),
      });
      return;
    }

    if (path.startsWith("dashboard/unified-savings")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_UNIFIED_SAVINGS),
      });
      return;
    }

    if (path.startsWith("dashboard/time-saved")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_TIME_SAVED),
      });
      return;
    }

    if (path.startsWith("harness/snapshot")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_HARNESS_SNAPSHOT),
      });
      return;
    }

    if (path.startsWith("harness/intelligence-scan")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_HARNESS_INTELLIGENCE_SCAN),
      });
      return;
    }

    if (path.startsWith("harness/pattern-explorer")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_PATTERN_EXPLORER),
      });
      return;
    }

    if (path.startsWith("harness/rubric-templates/evaluate")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          is_valid: true,
          confidence: 0.86,
          feedback: "Strong sample.",
          rubric_template_id: "copy-marketing",
        }),
      });
      return;
    }

    if (path.startsWith("harness/closed-review-loop/run")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          passed: true,
          turns_used: 2,
          max_turns: 5,
          min_score_label: "4.0/5",
          template_name: "Marketing Creative (Riverflow)",
          final_text: "Revised campaign copy with explicit CTA.",
          iterations: [
            { turn: 1, score: 0.62, is_valid: false, passed: false, feedback: "CTA vague" },
            { turn: 2, score: 0.88, is_valid: true, passed: true, feedback: "Pass" },
          ],
          message: "Rubric pass on turn 2 (score 88%).",
        }),
      });
      return;
    }

    if (path.startsWith("harness/rubric-templates")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { id: "copy-marketing", name: "Marketing Copy", category: "copy", pass_threshold: 0.7 },
          { id: "marketing-creative", name: "Marketing Creative", category: "copy", pass_threshold: 0.75 },
          { id: "brand-compliance", name: "Brand Compliance", category: "copy", pass_threshold: 0.8 },
        ]),
      });
      return;
    }

    if (path.startsWith("memory/episodic/daily-log")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_EPISODIC_DAILY_LOG),
      });
      return;
    }

    if (path.startsWith("memory/episodic/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_EPISODIC_SUMMARY),
      });
      return;
    }

    if (path.startsWith("memory/episodic/timeline")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_EPISODIC_TIMELINE),
      });
      return;
    }

    if (path.startsWith("dashboard/task-queue")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_TASK_QUEUE),
      });
      return;
    }

    if (path.startsWith("dump-sleep/overnight-report/voice")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available: true,
          batch_id: "d1111111-1111-4111-8111-111111111111",
          script_text: "Good morning. Here is your overnight swarm report.",
          audio_base64: "",
          content_type: "audio/mpeg",
          provider: "stub",
          window_hours: 24,
          voice_disabled: true,
        }),
      });
      return;
    }

    if (path.startsWith("dump-sleep/overnight-report")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available: false,
          batch: null,
          window_hours: 24,
        }),
      });
      return;
    }

    if (path.startsWith("dump-sleep/batches")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "d1111111-1111-4111-8111-111111111111",
          status: "completed",
          file_count: 1,
          items_ingested: 1,
          stalled_signals: 0,
          pollen_earned: 2.5,
          briefing_md: "# Overnight Swarm Report\n",
          voice_note_present: false,
          created_at: new Date().toISOString(),
          processed_at: new Date().toISOString(),
          error_text: null,
        }),
      });
      return;
    }

    if (path.startsWith("llm-routing/local-inference/ping")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...STUB_LOCAL_INFERENCE,
          pings: [
            {
              provider: "ollama",
              ok: true,
              endpoint: "http://127.0.0.1:11434",
              model_count: 1,
              message: "Ollama reachable — 1 model(s) listed.",
            },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("llm-routing/local-inference")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_LOCAL_INFERENCE),
      });
      return;
    }

    if (path.startsWith("llm-routing/settings")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_LLM_ROUTING_SETTINGS),
      });
      return;
    }

    if (path.startsWith("llm-routing/cost-savings")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_LLM_COST_SAVINGS),
      });
      return;
    }

    if (path.startsWith("auto-graphify/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          available: false,
          batch: null,
          window_hours: 168,
        }),
      });
      return;
    }

    if (path.startsWith("auto-graphify/batches")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "g1111111-1111-4111-8111-111111111111",
          status: "completed",
          folder_label: "Research dump",
          file_count: 2,
          items_ingested: 2,
          graph_nodes_created: 6,
          vectors_embedded: 2,
          pollen_earned: 3.0,
          summary_md: "# Auto-Graphify ingest report\n",
          vault_rel_path: "graphify/demo/batch",
          created_at: new Date().toISOString(),
          processed_at: new Date().toISOString(),
          error_text: null,
        }),
      });
      return;
    }

    if (path.startsWith("dreaming/")) {
      if (path.includes("settings")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ enabled: true, frequency_hours: 24, routine_id: null }),
        });
        return;
      }
      if (route.request().method() === "DELETE" && path === "dreaming/cycles") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ cleared: 0 }),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("learning/bee-badges")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("dashboard/forager-goldmine-alerts")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FORAGER_GOLDMINE_ALERTS),
      });
      return;
    }

    if (path.startsWith("dashboard/foragers-overview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FORAGERS_OVERVIEW),
      });
      return;
    }

    if (path.startsWith("operator/costs/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_COST_SUMMARY),
      });
      return;
    }

    if (path.startsWith("auth/me")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_OPERATOR_ME),
      });
      return;
    }

    if (path.startsWith("auth/session-policy")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token_ttl_seconds: 1800,
          refresh_token_ttl_seconds: 604800,
          oauth_state_ttl_seconds: 600,
          rate_limit_per_minute: 100,
        }),
      });
      return;
    }

    if (path.startsWith("settings/team/audit-logs")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("settings/team")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ tenant_role: "admin", members: [], invites: [] }),
      });
      return;
    }

    if (path.startsWith("billing/usage")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_BILLING_USAGE),
      });
      return;
    }

    if (path.startsWith("billing/plans")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_BILLING_PLANS),
      });
      return;
    }

    if (path.startsWith("settings/enterprise/config")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_ENTERPRISE_CONFIG),
      });
      return;
    }

    if (path.startsWith("recipes/pattern-stacks")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_RECIPE_PATTERN_STACKS),
      });
      return;
    }

    if (/^recipes\/[^/]+\/routine$/.test(path)) {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            routine_id: "22222222-2222-4222-8222-222222222222",
            routine_name: "recipe-lead-gen-lane",
            recipe_id: "11111111-1111-4111-8111-111111111111",
            schedule_kind: "cron",
            roles: ["researcher", "critic"],
            webhook_url: null,
            webhook_token: null,
          }),
        });
        return;
      }
    }

    if (path.startsWith("recipes/marketplace-beta")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: false,
          generated_at: new Date().toISOString(),
          approved_count: 0,
          pending_count: 0,
          total_listings: 0,
          config: {},
        }),
      });
      return;
    }

    if (path.startsWith("recipes/search")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("recipes/match-config")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_RECIPE_MATCH_CONFIG),
      });
      return;
    }

    if (path === "recipes") {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_RECIPES_CATALOG),
      });
      return;
    }

    if (path.startsWith("recipes/skills-catalog")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SKILLS_CATALOG),
      });
      return;
    }

    if (path.startsWith("recipes/skills/unlocks")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SKILL_UNLOCKS),
      });
      return;
    }

    if (path.startsWith("learning/verified-pollen-leaderboard")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [] }) });
      return;
    }

    if (path.startsWith("external-apis/research-keys/status")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          providers: {
            tavily: { configured: false, masked: null },
            serper: { configured: false, masked: null },
          },
        }),
      });
      return;
    }

    if (path.startsWith("external-apis/providers")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ providers: [{ id: "billing", label: "Billing" }] }),
      });
      return;
    }

    if (path.startsWith("external-apis")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ apis: [] }) });
      return;
    }

    if (path.startsWith("auth/api-keys")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("llm-keys/voice-preferences")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          stt_provider: "auto",
          tts_provider: "auto",
          latency_mode: "balanced",
          vad_threshold: 0.7,
          silence_duration_ms: 700,
          tts_voice_id: "eve",
          tts_language: "auto",
          tts_tone: "none",
        }),
      });
      return;
    }

    if (path.startsWith("llm-keys")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ keys: [] }),
      });
      return;
    }

    if (path.startsWith("notifications")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ channels: [] }),
      });
      return;
    }

    if (path.startsWith("shares")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path === "operator/preview-decomposition" && route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_PREVIEW_DECOMPOSITION),
      });
      return;
    }

    if (path.startsWith("operator/mission-kanban/recipe-match")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_MISSION_KANBAN_RECIPE_MATCH),
      });
      return;
    }

    const agentConfigMatch = path.match(/^agents\/([^/]+)\/config$/);
    if (agentConfigMatch) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          system_prompt: "You are a scout bee.",
          output_format: "text",
          run_count: 3,
          schedule_value: "On demand",
        }),
      });
      return;
    }

    const agentIdMatch = path.match(/^agents\/([^/]+)$/);
    if (agentIdMatch && route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...STUB_AGENT, id: agentIdMatch[1] }),
      });
      return;
    }

    if (path.startsWith("agent-templates")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("agents?") || path === "agents") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([STUB_AGENT]),
      });
      return;
    }

    if (path.startsWith("outputs?") || path === "outputs") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
      return;
    }

    if (path.startsWith("dashboard/swarms-overview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SWARMS_OVERVIEW),
      });
      return;
    }

    if (path.startsWith("dashboard/swarm-board")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SWARM_BOARD),
      });
      return;
    }

    if (path.startsWith("hive-mind/search")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ query: "", results: [], generated_at: new Date().toISOString() }),
      });
      return;
    }

    if (path.startsWith("hive-mind/recall-settings")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recall_mode: "selective",
          token_budget_chars: 0,
          feature_enabled: true,
          max_prompt_chars: 4000,
          selective_max_chars: 2400,
        }),
      });
      return;
    }

    if (path.startsWith("hive-mind/recall-preview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          recall_mode: "selective",
          characters: 128,
          char_budget: 2400,
          hive_mind_prompt_block: "## HiveMind selective recall · graph-neighbour RAG\n- (sim≈0.82) stub hit",
        }),
      });
      return;
    }

    if (path.startsWith("memory/curated/cited-recall")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          query: "gumroad launch",
          in_memory: true,
          status: "found",
          answer: "Hero pack Gumroad listing draft with verified CTA and scorecard gate.",
          citations: [
            {
              source_id: "hive:hero-pack",
              source_type: "hive_mind",
              label: "HiveMind · hero-pack",
              snippet: "Hero pack Gumroad listing draft with CTA.",
              similarity: 0.86,
              href: "/knowledge?tab=outputs",
            },
            {
              source_id: "curated:mission",
              source_type: "curated_memory",
              label: "Brain Pack · Mission",
              snippet: "First sellable Gumroad harness this week.",
              similarity: 0.72,
              href: "/knowledge?tab=memory#brain-pack",
            },
          ],
          citation_count: 2,
          operator_hint: "Cited answer ready — open source links to verify before supervisor approve.",
        }),
      });
      return;
    }

    if (path === "memory/curated/tier0-injection-strip") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          visible: true,
          frozen_snapshot_label: "Hermes Brain Pack snapshot",
          recall_mode: "selective",
          deep_recall_budget_chars: 2400,
          chroma_enabled: true,
          operator_hint: "Tier-0 Brain Pack is injected on every Queen bootstrap before HiveMind vector search.",
          edit_href: "/knowledge?tab=memory#brain-pack",
          tiers: [
            {
              tier_id: "tier0",
              label: "Tier-0 · Brain Pack",
              order: 0,
              char_count: 820,
              estimated_tokens: 205,
              active: true,
              inject_timing: "Always — frozen Hermes snapshot before RAG",
              preview: "MISSION Ship Queenswarm SOUL Verify-first tone",
              sections: [
                {
                  section_id: "mission",
                  label: "Mission",
                  char_count: 120,
                  estimated_tokens: 30,
                  preview: "Ship Queenswarm daily harness",
                  filled: true,
                },
              ],
            },
            {
              tier_id: "tier1",
              label: "Tier-1 · Wiki hot tier",
              order: 1,
              char_count: 140,
              estimated_tokens: 35,
              active: true,
              inject_timing: "Hot tier wiki pages before deep raw search",
              preview: "WIKI LAYER Ops notes",
              sections: [],
            },
            {
              tier_id: "tier2",
              label: "Tier-2 · Chroma deep recall",
              order: 2,
              char_count: 2400,
              estimated_tokens: 600,
              active: true,
              inject_timing: "On query — vector + graph neighbours after tier-0/1",
              preview: "Budget 2400 chars · mode selective · runs after frozen Brain Pack snapshot.",
              sections: [],
            },
          ],
        }),
      });
      return;
    }

    if (path === "memory/curated/token-budget-meter") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          prompt_prefix_chars: 820,
          estimated_tokens: 205,
          storage_total_chars: 760,
          storage_max_chars: 96000,
          storage_usage_pct: 1,
          recall_mode: "selective",
          recall_char_budget: 2400,
          estimated_recall_tokens: 600,
          max_prompt_chars: 4000,
          selective_max_chars: 2400,
          recall_usage_pct: 60,
          combined_estimated_tokens: 805,
          status: "ok",
          operator_hint: "Selective recall keeps HiveMind injection under budget; Brain Pack injects on every Queen bootstrap.",
          layers: [
            { layer_id: "soul", label: "SOUL", char_count: 220, estimated_tokens: 55, filled: true },
            { layer_id: "memory", label: "MEMORY", char_count: 310, estimated_tokens: 77, filled: true },
            { layer_id: "user", label: "USER", char_count: 180, estimated_tokens: 45, filled: true },
            { layer_id: "brand", label: "BRAND", char_count: 50, estimated_tokens: 12, filled: true },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("memory/wiki-layer/")) {
      const stubOverview = {
        zones: {
          raw: { count: 0, items: [], description: "Raw sources" },
          wiki: { count: 0, char_count: 0, pages: [], description: "Compiled wiki" },
          instructions: { char_count: 0, preview: "", description: "Instructions" },
        },
        curated_prefix_chars: 0,
        wiki_chars: 0,
        settings: { retrieval_tier: "wiki_only", feature_enabled: true, telemetry: {} },
      };
      if (path === "memory/wiki-layer/overview") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(stubOverview) });
        return;
      }
      if (path === "memory/wiki-layer/settings") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ retrieval_tier: "wiki_only", feature_enabled: true, telemetry: {} }),
        });
        return;
      }
      if (path === "memory/wiki-layer/gardener/latest") {
        await route.fulfill({ status: 200, contentType: "application/json", body: "null" });
        return;
      }
      if (path === "memory/wiki-layer/capture" && route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ id: "capture-stub", markdown: "", topic_tags: ["second_brain:capture"] }),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      return;
    }

    if (path.startsWith("hive-mind/project-shape")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_PROJECT_SHAPE),
      });
      return;
    }

    if (path.startsWith("hive-mind/graph")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_HIVE_GRAPH),
      });
      return;
    }

    if (path === "hive-mind/memory-evolution/policy") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ auto_approve_enabled: false, include_high_importance: false }),
      });
      return;
    }

    if (path.startsWith("hive-mind/memory-evolution/proposals")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("agents/suggestions")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("agents/browser-sessions")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("agents/sessions/autonomy/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_AUTONOMY_SUMMARY),
      });
      return;
    }

    if (path.startsWith("agents/sessions/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessions_total: 0,
          status_counts: {},
          running_sessions: 0,
          needs_input_sessions: 0,
          completed_sessions: 0,
          routines_total: 0,
          active_routines: 0,
          due_routines: 0,
        }),
      });
      return;
    }

    if (path === "agents/sessions" || path.startsWith("agents/sessions?")) {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/loop-guardrails$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          status: "healthy",
          max_turns: 5,
          turns_used: 1,
          min_score_label: "4.0/5",
          last_rubric_score: null,
          cost_cap_usd: 0.5,
          spent_usd: 0.08,
          cost_utilization: 0.16,
          alerts: [],
          next_operator_action: "Loop within guardrails — continue or approve when critic passes.",
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/loop-timeline$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "needs_input",
          current_phase: "verify",
          progress_pct: 78,
          loop_chip: "Verify · 78%",
          phases: [
            {
              phase_id: "goal",
              label: "Goal",
              status: "done",
              summary: "Execution Studio pending approval session",
              event_count: 1,
              latest_at: new Date().toISOString(),
              highlights: ["Session objective set."],
            },
            {
              phase_id: "plan",
              label: "Plan",
              status: "done",
              summary: "2 sub-agent lane(s) planned.",
              event_count: 2,
              latest_at: new Date().toISOString(),
              highlights: ["Spawned researcher"],
            },
            {
              phase_id: "tool",
              label: "Tool",
              status: "done",
              summary: "2/2 sub-agents executed.",
              event_count: 4,
              latest_at: new Date().toISOString(),
              highlights: ["Researcher completed"],
            },
            {
              phase_id: "verify",
              label: "Verify",
              status: "active",
              summary: "Awaiting operator approve or input.",
              event_count: 1,
              latest_at: new Date().toISOString(),
              highlights: ["Approve publish pack"],
            },
          ],
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/tool-outcomes$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "needs_input",
          visible: true,
          pending_approval: true,
          approval_reason: "Critical action keyword detected: publish",
          tools: [
            {
              tool_name: "post_message",
              connector_slug: "slack",
              mode: "simulate",
              risk_tier: "write",
              args_summary: "channel=#launch, text=Ship day",
              result_summary: "Simulated: slack/post_message",
              simulated: true,
              executed: false,
              sub_agent_role: "publisher",
              event_type: "tool_execute",
              occurred_at: new Date().toISOString(),
            },
          ],
          critic: {
            score: 0.72,
            score_label: "3.6/5",
            min_score_label: "4.0/5",
            passed: false,
            feedback: "CTA weak — strengthen proof line before live publish.",
            source: "reflection",
          },
          operator_action: "Review simulate results and critic score below, then Approve to continue.",
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/checkpoint-resume-cta$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          visible: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "paused",
          runtime_mode: "durable",
          can_resume_from_checkpoint: true,
          resume_hint: "Resume from verified checkpoint after researcher → publisher.",
          last_verified_role: "researcher",
          next_resumable_role: "publisher",
          verified_steps: 1,
          total_steps: 2,
          loop_chip: "Checkpoint 1/2 → publisher",
          primary_label: "Resume from checkpoint",
          operator_guidance:
            "Verified through researcher. Resume continues at publisher without replaying completed lanes.",
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/report-rubric$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          visible: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "needs_input",
          pending_approval: true,
          template_id: "copy-marketing",
          template_name: "Marketing Copy",
          template_category: "copy",
          pass_threshold_pct: 70,
          score: 0.86,
          score_label: "4.3/5",
          min_score_label: "4.0/5",
          passed: true,
          pre_approve_status: "ready",
          feedback: "CTA is specific; headline could be shorter.",
          deliverable_preview: "Headline: Verified agent swarms for operators. CTA: Start free trial.",
          dimensions: [
            { id: "clarity", label: "Clarity", weight_pct: 30, prompt: "Can a skimming reader grasp the offer?" },
          ],
          must_satisfy: ["Single clear value proposition above the fold"],
          operator_hint: "Rubric meets verify floor — safe to approve live actions after tool outcome review.",
          evaluate_href: "/settings#harness-loops-rubric",
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/step-explainers$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          visible: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "needs_input",
          operator_hint: "Why this tool — without reading raw JSON events.",
          pattern_rationale: ["baseline: planning + multi-agent + RAG + guardrails"],
          chips: [
            {
              chip_id: "phase:tool:tool_use:post_message",
              phase_id: "tool",
              phase_label: "Tool",
              sub_agent_role: null,
              pattern_id: "tool_use",
              pattern_label: "Tool Use",
              tool_name: "post_message",
              tool_label: "Slack Post",
              explainer: "Execute actions via connectors instead of guessing. Tool: Slack Post.",
            },
            {
              chip_id: "sub:publisher:tool_use:post_message",
              phase_id: null,
              phase_label: null,
              sub_agent_role: "publisher",
              pattern_id: "tool_use",
              pattern_label: "Tool Use",
              tool_name: "post_message",
              tool_label: "Slack Post",
              explainer: "Execute actions via connectors instead of guessing. Tool: Slack Post.",
            },
          ],
        }),
      });
      return;
    }

    if (path.match(/^agents\/sessions\/[^/]+\/mid-flight-checkpoint$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          visible: true,
          session_id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          session_status: "needs_input",
          checkpoint_state: "needs_input",
          loop_phase: "verify",
          loop_chip: "Verify · 78%",
          headline: "Mid-flight checkpoint — approval required",
          operator_guidance: "Review tool outcomes and critic score, then Approve & continue or Reject & revise.",
          primary_action_id: "approve_continue",
          pending_approval: true,
          approval_reason: "Critical action keyword detected: publish",
          checkpoint: {
            can_resume_from_checkpoint: true,
            resume_hint: "Resume from verified checkpoint after researcher → publisher.",
            last_verified_role: "researcher",
            next_resumable_role: "publisher",
            verified_steps: 1,
            total_steps: 2,
          },
          actions: [
            {
              action_id: "pause_loop",
              label: "Pause loop",
              enabled: true,
              variant: "ghost",
              reason_disabled: null,
            },
            {
              action_id: "approve_continue",
              label: "Approve gate & continue",
              enabled: true,
              variant: "primary",
              reason_disabled: null,
            },
            {
              action_id: "reject_revise",
              label: "Reject & revise",
              enabled: true,
              variant: "danger",
              reason_disabled: null,
            },
            {
              action_id: "resume_session",
              label: "Resume session",
              enabled: false,
              variant: "secondary",
              reason_disabled: "Pause the loop first to use Resume session.",
            },
            {
              action_id: "resume_checkpoint",
              label: "Resume from checkpoint",
              enabled: true,
              variant: "secondary",
              reason_disabled: null,
            },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("agents/sessions/")) {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      if (
        path.includes("/events") ||
        path.includes("/audit-logs") ||
        path.includes("/context-history")
      ) {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
        return;
      }
      if (path.includes("/shared-context")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            enabled: false,
            matched_sections: [],
            sections: {},
            retrieval_contract: "",
            context_summary: {},
            pruned_items: 0,
            prompt_block: null,
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: path.split("/")[2] ?? "00000000-0000-4000-8000-000000000001",
          goal: "Execution Studio pending approval session",
          status: "needs_input",
          runtime_mode: "durable",
          created_by_subject: "dashboard:test",
          context_summary: {},
          swarm_id: null,
          task_id: null,
          started_at: null,
          completed_at: null,
          error_text: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          sub_agents: [],
        }),
      });
      return;
    }

    if (path.startsWith("agents/routines")) {
      if (route.request().method() !== "GET") {
        await route.fallback();
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(STUB_ROUTINES) });
      return;
    }

    if (path.startsWith("paper-trading/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_PAPER_TRADING),
      });
      return;
    }

    if (path.startsWith("dashboard/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SUMMARY),
      });
      return;
    }

    if (path.startsWith("solo-operator/grill-wizard/submit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          task_id: "00000000-0000-4000-8000-000000000099",
          deliverable_id: "00000000-0000-4000-8000-000000000098",
          title: "Stakeholder grill brief",
          href: "/tasks?task=00000000-0000-4000-8000-000000000099",
          session_href: null,
          message: "Brief saved to Mission Kanban triage and task workspace.",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/grill-wizard")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          min_answer_chars: 12,
          questions: [
            {
              id: "problem",
              title: "Problem / opportunity",
              prompt: "What problem or opportunity are you addressing?",
              hint: "No PII.",
            },
            {
              id: "kill_criteria",
              title: "Kill criteria",
              prompt: "What would make you stop?",
              hint: "",
            },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/video-url-batch/submit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          task_id: "00000000-0000-4000-8000-000000000090",
          deliverable_id: "00000000-0000-4000-8000-000000000091",
          title: "Video intel batch (1 URLs)",
          href: "/tasks?task=00000000-0000-4000-8000-000000000090",
          url_count: 1,
          ok_count: 1,
          partial_count: 0,
          error_count: 0,
          gardener_triggered: true,
          message: "Digest saved for 1 URLs — 1 OK, 0 partial, 0 failed. Wiki Gardener triggered.",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/video-url-batch")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          max_urls: 20,
          excerpt_chars: 1200,
          knowledge_href: "/knowledge?tab=wiki",
          tasks_href: "/tasks",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/campaign-launch-wizard/submit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          deliverable_id: "00000000-0000-4000-8000-000000000089",
          queue_status: "approved",
          simulate_ok: true,
          simulate_message: "Simulate OK",
          publish_queue_href: "/apps-tools/marketing-automation?section=queue#publish-queue",
          social_publish_href: "/apps-tools/marketing-automation?section=publish#social-publish",
          message: "Campaign pack archived and queue approved. Social simulate completed.",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/campaign-launch-wizard/rubric")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          passed: true,
          score: 0.82,
          pass_threshold: 0.75,
          template_id: "marketing-creative",
          template_name: "Marketing Creative (Riverflow)",
          feedback: "Strong CTA",
          message: "Rubric pass (82% ≥ 75%).",
        }),
      });
      return;
    }

    if (path.match(/^solo-operator\/campaign-launch-wizard\/draft$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          progress_pct: 50,
          steps: [
            { id: "brand_pack", label: "Pick brand pack", status: "done", detail: "Selected", link: null },
            { id: "draft_copy", label: "Draft copy", status: "done", detail: "Ready", link: null },
            { id: "rubric_score", label: "Rubric score", status: "pending", detail: "Run rubric", link: null },
            { id: "simulate_publish", label: "Simulate publish", status: "pending", detail: "Submit", link: null },
          ],
          brand_packs: [
            {
              id: "queenswarm-default",
              label: "Queenswarm default",
              source: "builtin",
              detail: "Default voice",
              ready: true,
            },
          ],
          draft: {
            brand_pack_id: "queenswarm-default",
            channel: "instagram",
            title: "Launch",
            body: "Campaign body for simulate-first publish lane.",
            cta: "Try now",
            hashtags: ["Queenswarm"],
            media_url: null,
          },
          rubric: {
            template_id: "marketing-creative",
            template_name: "Marketing Creative",
            score: null,
            pass_threshold: 0.75,
            passed: false,
            feedback: "",
          },
          deliverable_id: null,
          simulate_ok: null,
          simulate_message: "",
          links: {},
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/campaign-launch-wizard")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          progress_pct: 25,
          steps: [
            { id: "brand_pack", label: "Pick brand pack", status: "pending", detail: "Select pack", link: null },
            { id: "draft_copy", label: "Draft copy", status: "pending", detail: "Write copy", link: null },
            { id: "rubric_score", label: "Rubric score", status: "pending", detail: "Run rubric", link: null },
            { id: "simulate_publish", label: "Simulate publish", status: "pending", detail: "Submit", link: null },
          ],
          brand_packs: [
            {
              id: "queenswarm-default",
              label: "Queenswarm default",
              source: "builtin",
              detail: "Default voice",
              ready: true,
            },
          ],
          draft: {
            brand_pack_id: null,
            channel: "instagram",
            title: "",
            body: "",
            cta: "",
            hashtags: [],
            media_url: null,
          },
          rubric: {
            template_id: "marketing-creative",
            template_name: "Marketing Creative",
            score: null,
            pass_threshold: 0.75,
            passed: false,
            feedback: "",
          },
          deliverable_id: null,
          simulate_ok: null,
          simulate_message: "",
          links: {},
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/trading-thesis-wizard/submit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          task_id: "00000000-0000-4000-8000-000000000088",
          deliverable_id: "00000000-0000-4000-8000-000000000087",
          title: "Trading thesis brief",
          href: "/tasks?task=00000000-0000-4000-8000-000000000088",
          session_href: null,
          paper_cockpit_href: "/apps-tools/trading-automation?section=cockpit#trading-cockpit",
          message: "Thesis brief saved to Mission Kanban triage and task workspace.",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/trading-thesis-wizard")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          min_answer_chars: 10,
          paper_cockpit_href: "/apps-tools/trading-automation?section=cockpit#trading-cockpit",
          live_gate_skill: "real-money-risk-gate",
          questions: [
            {
              id: "market",
              title: "Market / event",
              prompt: "Which market?",
              hint: "",
            },
            {
              id: "kill_criteria",
              title: "Kill criteria",
              prompt: "When exit?",
              hint: "",
            },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/closed-loop-presets/apply")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          preset_id: "factory_forge",
          label: "Skill Factory critic loop",
          rubric_template_id: "code-review",
          max_turns: 6,
          min_score: 0.8,
          message: "Applied Skill Factory critic loop — LOOP2 guardrails updated.",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/closed-loop-presets")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          active_preset_id: "factory_forge",
          active_rubric_template_id: "code-review",
          presets: [
            {
              preset_id: "factory_forge",
              label: "Skill Factory critic loop",
              description: "Forge queue builds",
              lane: "factory",
              rubric_template_id: "code-review",
              max_turns: 6,
              min_score: 0.8,
              simulate_only: false,
              href: "/factory?tab=queue",
            },
          ],
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/loop-guardrails")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          max_turns: 5,
          min_score: 0.8,
          cost_cap_usd: 0.5,
          cost_warn_ratio: 0.6,
          source: "deployment",
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/first-run")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          complete: false,
          progress_pct: 33,
          steps: [
            {
              id: "llm_keys",
              label: "LLM keys",
              detail: "Add at least one provider.",
              done: false,
              href: "/settings/llm-keys",
              link_label: "Open LLM keys",
            },
          ],
          capability: {
            headline: "Your verified agent operating system",
            subhead: "Queenswarm runs supervisor missions with simulate-first verify.",
            bullets: ["One Process Rail", "Mission Kanban", "Brain Pack"],
          },
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/mission-home")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          generated_at: new Date().toISOString(),
          current_step: "plan",
          process_steps: [
            { id: "setup", label: "Setup", short_label: "Setup" },
            { id: "plan", label: "Plan", short_label: "Plan" },
            { id: "work", label: "Work", short_label: "Work" },
            { id: "verify", label: "Verify", short_label: "Verify" },
            { id: "learn", label: "Learn", short_label: "Learn" },
            { id: "done", label: "Done", short_label: "Done" },
          ],
          brief_bullets: [{ text: "Life OS: triage ready.", source: "trio" }],
          next_actions: [
            {
              id: "po_supervisor_brief",
              title: "Bank PO brief",
              detail: "Start a supervisor session.",
              href: "/agents?preset=bank-po-brief",
              priority: 2,
            },
          ],
          approvals: [],
          active_sessions: [],
          memory_strip: {
            layers: [
              {
                id: "soul",
                label: "SOUL",
                preview: "Verify-first bee hive.",
                char_count: 24,
                filled: true,
                href: "/knowledge?tab=memory#brain-pack",
              },
            ],
            total_chars: 24,
            max_chars: 80000,
            usage_pct: 0,
          },
          step_studios: [
            {
              id: "session_presets",
              title: "Goal templates",
              detail: "Pick a structured supervisor preset.",
              href: "/agents#sessions",
            },
          ],
          first_run_complete: true,
          rapid_loop_widget_enabled: true,
          links: {
            new_session: "/agents#sessions",
            approvals: "/cockpit#approvals",
            knowledge: "/knowledge#memory",
            kanban: "/tasks",
          },
        }),
      });
      return;
    }

    if (path.startsWith("solo-operator/mission-feed")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ events: [], unread: 0, total: 0 }),
      });
      return;
    }

    if (path.startsWith("solo-operator/mission-search/backfill-auto")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, auto_skipped: true, reason: "tenant_backfill_recent" }),
      });
      return;
    }

    if (path.startsWith("solo-operator/mission-search")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ query: "", sessions: [], tasks: [], total: 0 }),
      });
      return;
    }

    if (path.startsWith("swarms?") || path === "swarms") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([{ id: "s1111111-1111-4111-8111-111111111111", name: "Scout Swarm", is_active: true }]),
      });
      return;
    }

    if (path.startsWith("auth/tenants")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ tenants: [], active_tenant_id: null }),
      });
      return;
    }

    if (path.startsWith("foragers/discovery-wizard/bind")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          forager_id: "e2e-discovery-forager",
          forager_name: "E2E Discovery Forager",
          niche: "jobs",
          source_type: "rss",
          urls_bound: ["https://jobs.example.com/feed.xml"],
          created: true,
          message: "Discovery URLs bound.",
        }),
      });
      return;
    }

    if (path.startsWith("foragers/discovery-wizard/search")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FORAGER_DISCOVERY_SEARCH),
      });
      return;
    }

    if (path.startsWith("foragers/discovery-wizard")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FORAGER_DISCOVERY_WIZARD),
      });
      return;
    }

    if (path.startsWith("foragers/data-monitor-wizard/submit")) {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ok: true,
          forager_id: "e2e-data-monitor-forager",
          forager_name: STUB_DATA_MONITOR_PLAN.forager_name,
          niche: "jobs",
          source_type: "rss",
          extract_schema: "jobs",
          schedule_label: "every 24h",
          skill_bundle: STUB_DATA_MONITOR_PLAN.skill_bundle,
          routine_triggered: true,
          message: "Data monitor created.",
        }),
      });
      return;
    }

    if (path.startsWith("foragers/data-monitor-wizard/preview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_DATA_MONITOR_PLAN),
      });
      return;
    }

    if (path.startsWith("foragers/data-monitor-wizard")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_DATA_MONITOR_WIZARD),
      });
      return;
    }

    if (path === "foragers" || path.startsWith("foragers?")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path === "workflows" || path.startsWith("workflows?")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("tools/hub/overview")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          registry: [],
          featured_presets: [
            {
              id: "venice_mcp",
              title: "Venice AI · MCP Hub",
              installed: false,
              featured: true,
              cost_tier: "medium",
              latency_tier: "balanced",
              tool_count: 9,
            },
          ],
          venice_preset: {
            id: "venice_mcp",
            title: "Venice AI · MCP Hub",
            installed: false,
            tool_count: 9,
          },
          totals: { installed_tools: 0, active_presets: 0, featured_count: 1 },
        }),
      });
      return;
    }

    if (path.startsWith("connectors/dynamic")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
      return;
    }

    if (path.startsWith("external/projects")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
      return;
    }

    if (path === "plugins" || path.startsWith("plugins?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ installed: [], reload_generation: 1 }),
      });
      return;
    }

    if (path.startsWith("system/status")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          redis_ok: true,
          celery_ok: true,
          db_ok: true,
          llm_ok: true,
          llm_grok: true,
          llm_anthropic: false,
          agents_total: 1,
          agents_running: 0,
          tasks_running: 0,
          tasks_pending: 0,
          host_cpu_percent: 12,
          host_memory_percent: 40,
          host_disk_percent: 30,
          llm_concurrency_limit: 4,
          llm_in_flight: 0,
          simulation_concurrency_limit: 2,
          simulation_in_flight: 0,
          simulation_enabled: true,
          simulation_tasks_running: 0,
          simulation_tasks_pending: 0,
          resource_pressure: false,
          resource_pressure_reason: "",
        }),
      });
      return;
    }

    if (path === "tasks" || path.startsWith("tasks?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_MISSION_KANBAN_TASKS),
      });
      return;
    }

    if (path === "operator/apps-tools-index" || path.startsWith("operator/apps-tools-index?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_APPS_TOOLS_INDEX),
      });
      return;
    }

    if (path.startsWith("skill-factory/snapshot")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SKILL_FACTORY_SNAPSHOT),
      });
      return;
    }

    if (path.startsWith("factory-readiness/llm")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_FACTORY_LLM_READINESS),
      });
      return;
    }

    if (path.startsWith("skill-factory/seeds") || path.startsWith("skill-factory/llm-readiness")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          vertical: ["indie hacker SEO"],
          starter: ["SEO blog pipeline"],
          product_presets: [],
          ready: true,
          blockers: [],
        }),
      });
      return;
    }

    if (path.startsWith("operator/apps-tools-index/analytics")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_APPS_TOOLS_ANALYTICS),
      });
      return;
    }

    if (path.match(/^tasks\/[^/]+\/lineage$/)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          task: STUB_MISSION_KANBAN_TASKS[0],
          parent: null,
          children: STUB_MISSION_KANBAN_TASKS.slice(1, 3),
          goal_progress: {
            enabled: true,
            visible: true,
            task_id: STUB_MISSION_KANBAN_TASKS[0]?.id ?? "00000000-0000-4000-8000-000000000001",
            session_id: "00000000-0000-4000-8000-000000000099",
            session_status: "running",
            session_href: "/agents?session=00000000-0000-4000-8000-000000000099#sessions",
            goal_preview: "Content week launch pack",
            progress_pct: 62,
            loop_chip: "Tool · 62%",
            current_phase: "tool",
            durable_steps_done: 1,
            durable_steps_total: 2,
            phases: [
              { phase_id: "goal", label: "Goal", status: "done" },
              { phase_id: "plan", label: "Plan", status: "done" },
              { phase_id: "tool", label: "Tool", status: "active" },
              { phase_id: "verify", label: "Verify", status: "pending" },
            ],
            headline: "Supervisor session · Tool · 62%",
          },
        }),
      });
      return;
    }

    if (path.startsWith("tasks/")) {
      const method = route.request().method();
      if (method === "DELETE") {
        await route.fulfill({ status: 204, body: "" });
        return;
      }
      if (method === "PATCH") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...STUB_MISSION_KANBAN_TASKS[0], title: "Content week (edited)" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_MISSION_KANBAN_TASKS[0]),
      });
      return;
    }

    if (path === "tasks/bulk-cancel") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ cancelled: 1, skipped_running: 0, not_found: 0 }),
      });
      return;
    }

    if (path.startsWith("ballroom/")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      return;
    }

    if (path === "virtual-company/bootstrap-checklist" || path.startsWith("virtual-company/bootstrap-checklist?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          profile_complete: true,
          routing_mode: "solo",
          free_first_active: false,
          departments_ready: 0,
          departments_total: 0,
          next_steps: [],
          connectors: [],
        }),
      });
      return;
    }

    if (path === "virtual-company/oauth-setup-guide" || path.startsWith("virtual-company/oauth-setup-guide?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ redirect_uri: "http://localhost:4310/api/auth/callback/oauth" }),
      });
      return;
    }

    if (path === "oauth/providers" || path.startsWith("oauth/providers?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ providers: [] }),
      });
      return;
    }

    if (path === "execution-studio/overview" || path.startsWith("execution-studio/overview?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_EXECUTION_STUDIO_OVERVIEW),
      });
      return;
    }

    if (path === "execution-studio/pending-approvals" || path.startsWith("execution-studio/pending-approvals?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ count: 0, browser_pending: 0, external_pending: 0, codebase_pending: 0, live_actions: [] }),
      });
      return;
    }

    if (path === "execution-studio/manual" || path.startsWith("execution-studio/manual?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          version: "1",
          title: "Manual",
          summary: "Guide",
          sections: [{ id: "overview", title: "Overview", content_md: "Hello" }],
        }),
      });
      return;
    }

    if (path.startsWith("tools/super-routers")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], presets: [] }),
      });
      return;
    }

    await route.fallback();
  });
}
