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

const STUB_INNOVATION_LAB = {
  enabled: true,
  proposals: [],
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

const STUB_COST_SUMMARY = {
  window_days: 35,
  series: [{ day: new Date().toISOString().slice(0, 10), spend_usd: 1.25, model: "grok" }],
};

const STUB_FORAGERS_OVERVIEW = {
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
  solo_mode: false,
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

    if (path === "operator/innovation-lab" || path.startsWith("operator/innovation-lab?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_INNOVATION_LAB),
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
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
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

    if (path.startsWith("operator/apps-tools-index/analytics")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_APPS_TOOLS_ANALYTICS),
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
