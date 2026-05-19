import type { Page } from "@playwright/test";

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
  items: [],
  pending_count: 0,
  running_count: 0,
  completed_today_count: 0,
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

const STUB_OPERATOR_ME = {
  id: "dash:00000000-0000-4000-8000-000000000001",
  email: "operator@queenswarm.love",
  display_name: "Playwright Operator",
  twofa_enabled: false,
  twofa_pending: false,
  backup_codes_remaining: 0,
};

export const STUB_AGENT_ID = STUB_AGENT.id;

const STUB_BILLING_USAGE = {
  tenant_id: "00000000-0000-4000-8000-000000000001",
  tier: "free",
  status: "active",
  stripe_customer_id: null,
  stripe_subscription_id: null,
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
  plans: [
    {
      tier: "free",
      label: "Free hive",
      limits: {
        monthly_tokens_hard: 100000,
        monthly_supervisor_sessions_hard: 50,
        monthly_external_calls_hard: 500,
        storage_mb_hard: 512,
      },
      features: { ballroom: true },
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
  stripe_checkout_ready: false,
  unlocked_recipe_ids: [] as string[],
  premium_price_eur_cents_default: 1900,
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
 * Stubs common proxy routes so authenticated shell E2E runs without a live hive backend.
 *
 * Server Components still SSR without backend — pages degrade gracefully with empty initial data.
 */
export async function installShellApiMocks(page: Page): Promise<void> {
  await page.route("**/api/proxy/**", async (route) => {
    const url = route.request().url();
    const path = new URL(url).pathname.replace(/^\/api\/proxy\/?/, "");

    if (path.startsWith("dashboard/task-queue")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_TASK_QUEUE),
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

    if (path.startsWith("external-apis/providers")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ providers: [{ id: "stripe", label: "Stripe" }] }),
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

    if (path.startsWith("dashboard/summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_SUMMARY),
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

    if (path.startsWith("connectors/dynamic")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
      return;
    }

    if (path.startsWith("agents/sessions")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("agents/routines")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
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

    if (path.startsWith("tasks?")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (path.startsWith("ballroom/")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
      return;
    }

    await route.fallback();
  });
}
