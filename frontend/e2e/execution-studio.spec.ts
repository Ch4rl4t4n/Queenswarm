import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const executionStudioE2eEnabled = process.env.E2E_EXECUTION_STUDIO === "1";

const STUDIO_OVERVIEW = {
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
  notifications: {
    email_recipients: [],
    slack_webhook_url: "",
    discord_webhook_url: "",
    teams_webhook_url: "",
    web_push_configured: false,
    web_push_subscribed: false,
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

test.describe("Execution Studio tab", () => {
  test.beforeEach(async ({ context, baseURL, page }) => {
    test.skip(!executionStudioE2eEnabled, "Set E2E_EXECUTION_STUDIO=1 to run Execution Studio checks.");

    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);

    await page.route("**/api/proxy/execution-studio/overview", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUDIO_OVERVIEW),
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
  });

  test("workspace shows telemetry and browser fallback controls", async ({ page }) => {
    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Execution Studio/i }).first()).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByRole("paragraph").filter({ hasText: "Tool runs" })).toBeVisible();
    await expect(page.getByText("Cost blocks")).toBeVisible();
    await expect(page.getByText("Per-connector activity")).toBeVisible();
    await expect(page.getByText("Connector activity chart")).toBeVisible();
    await expect(page.getByText("Activity over time (hourly)")).toBeVisible();
    await expect(page.getByText("2 runs")).toBeVisible();
    await expect(page.getByRole("button", { name: /Test browser fallback/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Confirm live browser step/i })).toBeVisible();
    await expect(page.getByText("Recent activity")).toBeVisible();
  });

  test("manual tab loads sections", async ({ page }) => {
    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: /Manual/i }).click();
    await expect(page.getByText("Overview")).toBeVisible({ timeout: 20_000 });
  });

  test("proposal approve triggers maintainer handoff", async ({ page }) => {
    let reviewCalled = false;

    await page.route("**/api/proxy/execution-studio/proposals/*/review", async (route) => {
      reviewCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
          status: "approved",
          handoff: { ok: true, session_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb" },
        }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByText("Pending codebase proposals")).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: /^Approve$/i }).first().click();
    await expect.poll(() => reviewCalled).toBe(true);
  });

  test("confirm live browser step posts operator_confirmed", async ({ page }) => {
    let liveBody: Record<string, unknown> | null = null;

    await page.route("**/api/proxy/execution-studio/browser/step", async (route) => {
      if (route.request().method() === "POST") {
        liveBody = route.request().postDataJSON() as Record<string, unknown>;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, mode: "live", message: "Live browser step OK" }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: /Confirm live browser step/i }).click();
    await expect.poll(() => liveBody?.mode).toBe("live");
    await expect.poll(() => liveBody?.operator_confirmed).toBe(true);
  });

  test("confirm live external connector posts operator_confirmed", async ({ page }) => {
    let executeBody: Record<string, unknown> | null = null;

    await page.route("**/api/proxy/execution-studio/execute", async (route) => {
      if (route.request().method() === "POST") {
        executeBody = route.request().postDataJSON() as Record<string, unknown>;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, mode: "live", message: "Live connector OK" }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: /Confirm live connector/i }).click();
    await expect.poll(() => executeBody?.mode).toBe("live");
    await expect.poll(() => executeBody?.operator_confirmed).toBe(true);
    await expect.poll(() => executeBody?.connector_slug).toBe("notion_workspace");
  });

  test("teams webhook test posts channel filter", async ({ page }) => {
    let testBody: Record<string, unknown> | null = null;

    await page.route("**/api/proxy/execution-studio/notifications/test-webhooks", async (route) => {
      if (route.request().method() === "POST") {
        testBody = route.request().postDataJSON() as Record<string, unknown>;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ teams: true, slack: false, discord: false }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Execution Studio/i }).first()).toBeVisible({
      timeout: 45_000,
    });
    await page.getByRole("button", { name: "Test Teams webhook" }).click();
    await expect.poll(() => testBody?.channels).toEqual(["teams"]);
  });

  test("supervisor context panel loads audit excerpt", async ({ page }) => {
    const sessionId = "cccccccc-cccc-4ccc-cccc-cccccccccccc";

    await page.route(`**/api/proxy/agents/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: sessionId,
          goal: "Verify connector pricing page after failure",
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
          sub_agents: [
            {
              id: "dddddddd-dddd-4ddd-dddd-dddddddddddd",
              role: "researcher",
              status: "failed",
              runtime_mode: "durable",
              toolset: [],
              short_memory: {},
              spawn_order: 1,
              started_at: null,
              completed_at: null,
              last_output: null,
              error_text: "Connector timeout on notion_workspace/search",
            },
          ],
        }),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/audit-logs**`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "eeeeeeee-eeee-4eee-eeee-eeeeeeeeeeee",
            tenant_id: "ffffffff-ffff-4fff-ffff-ffffffffffff",
            action: "supervisor_session_control",
            target_type: "supervisor_session",
            target_ref: sessionId,
            actor_user_id: null,
            payload: { control_action: "pause", message: "Awaiting operator live confirm" },
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByText("Supervisor session context")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Connector timeout on notion_workspace/search")).toBeVisible();
    await expect(page.getByText("control: pause")).toBeVisible();
  });

  test("digest email test button calls test-email endpoint", async ({ page }) => {
    let emailTestCalled = false;

    await page.route("**/api/proxy/execution-studio/notifications/test-email", async (route) => {
      emailTestCalled = route.request().method() === "POST";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ sent: true, recipient_count: 1 }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: "Test digest email" }).click();
    await expect.poll(() => emailTestCalled).toBe(true);
    await expect(page.getByLabel("Digest email test passed")).toBeVisible({ timeout: 10_000 });
  });

  test("slack webhook test shows inline success status", async ({ page }) => {
    await page.route("**/api/proxy/execution-studio/notifications/test-webhooks", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ slack: true, discord: false, teams: false }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: "Test Slack webhook" }).click();
    await expect(page.getByLabel("Slack test passed")).toBeVisible({ timeout: 10_000 });
  });

  test("weekly digest preview loads formatted body", async ({ page }) => {
    await page.route("**/api/proxy/execution-studio/notifications/weekly-rollup-preview", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Weekly Execution Studio rollup for *Acme Hive*\nTool runs: 2",
          email_body: "Weekly Execution Studio rollup for Acme Hive\nTool runs: 2",
          last_sent_at: null,
        }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: "Preview weekly digest" }).click();
    await expect(page.getByLabel("Weekly digest preview")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Slack" })).toBeVisible();
    await expect(page.getByText("Acme Hive")).toBeVisible();
  });

  test("send weekly digest preview posts send endpoint", async ({ page }) => {
    let sendCalled = false;

    await page.route("**/api/proxy/execution-studio/notifications/send-weekly-rollup-preview", async (route) => {
      sendCalled = route.request().method() === "POST";
      const body = route.request().postDataJSON() as { channels?: string[] };
      expect(body.channels).toEqual(["slack", "discord", "teams"]);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, channels: { slack: true, email: true } }),
      });
    });
    await page.route("**/api/proxy/execution-studio/notifications/weekly-rollup-preview", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Weekly Execution Studio rollup for *Acme Hive*",
          email_body: "Weekly Execution Studio rollup for Acme Hive",
          last_sent_at: null,
        }),
      });
    });

    await page.goto("/integrations?tab=studio", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: "Preview weekly digest" }).click();
    await page.getByRole("button", { name: "Send selected" }).click();
    await expect.poll(() => sendCalled).toBe(true);
  });
});
