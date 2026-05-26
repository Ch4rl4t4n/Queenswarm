import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const supervisorFlowEnabled = process.env.E2E_EXECUTION_STUDIO_SUPERVISOR === "1";

const SUPERVISOR_STUDIO_OVERVIEW = {
  enabled: true,
  policy: {
    default_mode: "simulate",
    live_requires_approval: true,
    simulate_allows_read_calls: true,
    codebase_default_mode: "simulate",
    live_codebase_requires_approval: true,
    codebase_pr_only: true,
  },
  stats: { active: 1, needs_credentials: 0, ready_to_test: 0, inactive: 0 },
  connections: [],
  packs: [],
  setup_steps: [],
  codebase: {
    lane: "internal",
    queen_maintainer_enabled: true,
    tech_health: { health_score: 0.8, signals: [], backend_pinned_deps: 1, frontend_deps: 1 },
    maintainer_routine: { enabled: false, routine_id: null },
    github_repo: { owner: "org", repo: "app", configured: true },
    repo_connector: null,
    pr_only: true,
    denylist_prefixes: [".env"],
    agent_roles: ["researcher"],
    agent_skills: ["execution-studio"],
    setup_steps: [],
  },
  manual: { version: "1", title: "Manual", summary: "Guide", section_count: 1 },
  pending_codebase_proposals: [],
  recent_activity: [
    {
      event_type: "browser_step",
      message: "Browser live step pending operator approval",
      at: new Date().toISOString(),
    },
    {
      event_type: "proposal_created",
      message: "External lane proposal: External execution lane (researcher)",
      at: new Date().toISOString(),
    },
    {
      event_type: "tool_execute",
      message: "Auto-simulate external proposal: slack_workspace/post_message",
      at: new Date().toISOString(),
    },
  ],
  activity_telemetry: {
    total_events: 3,
    by_event_type: { browser_step: 1, proposal_created: 1, tool_execute: 1 },
    by_connector: { slack_workspace: 1 },
    connector_cost_blocks: {},
    connector_chart: [{ slug: "slack_workspace", runs: 1, blocks: 0 }],
    activity_time_series: [{ bucket: "2026-05-21T12", runs: 1, blocks: 0 }],
    tool_executes: 1,
    browser_steps: 1,
    proposals_created: 1,
    maintainer_runs: 0,
    cost_tier_blocks: 0,
    window_limit: 40,
  },
  pending_approvals: {
    count: 2,
    browser_pending: 1,
    external_pending: 1,
    codebase_pending: 0,
    live_actions: [
      { type: "browser", message: "Browser live step pending operator approval" },
      {
        type: "external",
        connector_slug: "slack_workspace",
        tool_name: "post_message",
        message: "External live pending approval: slack_workspace/post_message",
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

test.describe("Execution Studio supervisor failure chain", () => {
  test.beforeEach(async ({ context, baseURL, page }) => {
    test.skip(!supervisorFlowEnabled, "Set E2E_EXECUTION_STUDIO_SUPERVISOR=1 to run supervisor flow checks.");

    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);

    await page.route("**/api/proxy/execution-studio/overview", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SUPERVISOR_STUDIO_OVERVIEW),
      });
    });
    await page.route("**/api/proxy/tools/super-routers", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], presets: [] }),
      });
    });
    await page.route("**/api/proxy/execution-studio/pending-approvals", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SUPERVISOR_STUDIO_OVERVIEW.pending_approvals),
      });
    });
  });

  test("shows pending browser banner and connector chart after supervisor failure chain", async ({ page }) => {
    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByText("Pending live confirmations")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Confirm live connector")).toBeVisible();
    await expect(page.getByText("Activity over time (hourly)")).toBeVisible();
    await expect(page.getByText("Connector activity chart")).toBeVisible();
  });
});
