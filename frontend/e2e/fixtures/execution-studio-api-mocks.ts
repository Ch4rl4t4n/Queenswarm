import type { Page } from "@playwright/test";

/** Minimal Execution Studio overview for shell / tab E2E (no live backend). */
export const STUB_EXECUTION_STUDIO_OVERVIEW = {
  enabled: true,
  policy: {
    default_mode: "simulate",
    live_requires_approval: true,
    simulate_allows_read_calls: true,
    codebase_default_mode: "simulate",
    live_codebase_requires_approval: true,
    codebase_auto_approve_enabled: false,
    codebase_pr_only: true,
  },
  stats: { active: 1, needs_credentials: 0, ready_to_test: 0, inactive: 0 },
  notifications: {
    email_recipients: ["ops@queenswarm.love"],
    slack_webhook_url: "https://hooks.slack.com/services/T000/B000/XXX",
    discord_webhook_url: "",
    teams_webhook_url: "https://outlook.office.com/webhook/stub",
    web_push_configured: false,
    web_push_subscribed: false,
    weekly_rollup_enabled: true,
  },
  connections: [
    {
      id: "c1",
      slug: "notion_workspace",
      display_name: "Notion",
      auth_type: "oauth2",
      status: "active",
      is_active: true,
      tools_count: 3,
      allowed_manager_slugs: ["execution_operations"],
      template_id: "notion_workspace",
    },
  ],
  packs: [],
  setup_steps: [],
  codebase: {
    lane: "internal",
    queen_maintainer_enabled: true,
    tech_health: { health_score: 0.82, signals: [], backend_pinned_deps: 1, frontend_deps: 2 },
    maintainer_routine: { enabled: false, routine_id: null },
    github_repo: { owner: "org", repo: "app", configured: true },
    repo_connector: null,
    pr_only: true,
    denylist_prefixes: [".env"],
    agent_roles: ["researcher"],
    agent_skills: ["execution-studio"],
    setup_steps: [],
  },
  manual: { version: "1", title: "Manual", summary: "Guide", section_count: 7 },
  pending_codebase_proposals: [
    {
      id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
      title: "Refactor connector refresh",
      description: "Dual-write OAuth refresh to hub.",
      proposed_by_role: "researcher",
      risk_level: "medium",
      goal_excerpt: "Implement token refresh dual-write in dynamic hub.",
      created_at: new Date().toISOString(),
    },
  ],
  recent_activity: [
    {
      event_type: "tool_execute",
      message: "Simulated: notion_workspace/search",
      at: new Date().toISOString(),
    },
  ],
  activity_telemetry: {
    total_events: 2,
    by_event_type: { tool_execute: 2 },
    by_connector: { notion_workspace: 2 },
    connector_cost_blocks: { notion_workspace: 1 },
    connector_chart: [{ slug: "notion_workspace", runs: 2, blocks: 1 }],
    activity_time_series: [{ bucket: "2026-05-21T12", runs: 2, blocks: 1 }],
    tool_executes: 2,
    browser_steps: 0,
    proposals_created: 0,
    maintainer_runs: 0,
    cost_tier_blocks: 1,
    window_limit: 40,
  },
  pending_approvals: {
    count: 1,
    browser_pending: 0,
    external_pending: 1,
    codebase_pending: 0,
    live_actions: [
      {
        type: "external",
        connector_slug: "notion_workspace",
        tool_name: "search",
        message: "External live pending approval: notion_workspace/search",
        supervisor_session_id: "cccccccc-cccc-4ccc-cccc-cccccccccccc",
      },
    ],
  },
  media_registry: { pack_id: "media", label: "Media", items: [] },
  browser_fallback: {
    enabled: true,
    role: "browser_operator",
    lane: "fallback",
    description: "Browser harness fallback lane.",
    sessions_api: "/api/v1/agent-sessions/browser-harness/sessions",
    execute_api: "/api/v1/execution-studio/browser/step",
    supervisor_role: "browser_operator",
  },
  super_routers: { count: 0, active_count: 0, items: [] },
};

/** Clear sub-nav prefs that can hide Execution Studio or Analytics despite deep links. */
export async function clearIntegrationsSubnavPrefs(page: Page): Promise<void> {
  await page.addInitScript(() => {
    for (const key of [
      "queenswarm:subnav-disabled:integrations-primary",
      "queenswarm:subnav-disabled:execution-studio-workspace",
      "queenswarm:subnav-disabled:execution-studio-panel",
    ]) {
      localStorage.removeItem(key);
    }
  });
}

/** Route Execution Studio proxy endpoints for tab E2E. */
export async function installExecutionStudioApiMocks(page: Page): Promise<void> {
  await page.route("**/api/proxy/execution-studio/overview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STUB_EXECUTION_STUDIO_OVERVIEW),
    });
  });
  await page.route("**/api/proxy/execution-studio/pending-approvals", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ count: 0, browser_pending: 0, external_pending: 0, codebase_pending: 0, live_actions: [] }),
    });
  });
  await page.route("**/api/proxy/execution-studio/manual", async (route) => {
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
  });
  await page.route("**/api/proxy/tools/super-routers", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], presets: [] }),
    });
  });
  await page.route("**/api/proxy/execution-studio/notifications", async (route) => {
    if (route.request().method() !== "PATCH") {
      await route.fallback();
      return;
    }
    const body = (route.request().postDataJSON() ?? {}) as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        notifications: {
          email_recipients: body.email_recipients ?? [],
          slack_webhook_url: body.slack_webhook_url ?? "",
          discord_webhook_url: body.discord_webhook_url ?? "",
          teams_webhook_url: body.teams_webhook_url ?? "",
          telegram_bot_token: body.telegram_bot_token ?? "",
          telegram_chat_id: body.telegram_chat_id ?? "",
          web_push_configured: false,
          web_push_subscribed: false,
          weekly_rollup_enabled: true,
        },
      }),
    });
  });
}
