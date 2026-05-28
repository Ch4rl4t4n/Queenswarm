import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import {
  clearIntegrationsSubnavPrefs,
  installExecutionStudioApiMocks,
} from "./fixtures/execution-studio-api-mocks";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const executionStudioE2eEnabled = process.env.E2E_EXECUTION_STUDIO === "1";

async function openExecutionStudioTab(
  page: import("@playwright/test").Page,
  section?: "overview" | "analytics" | "lanes" | "stack" | "publish" | "innovation",
): Promise<void> {
  const query = section ? `?tab=studio&section=${section}` : "?tab=studio";
  const overviewReady = page.waitForResponse(
    (res) => res.url().includes("/api/proxy/execution-studio/overview") && res.ok(),
    { timeout: 90_000 },
  );
  await page.goto(`/integrations${query}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "Integrations", exact: true })).toBeVisible({ timeout: 45_000 });
  await overviewReady;
  await expect(page.getByRole("heading", { name: /Execution Studio/i }).first()).toBeVisible({ timeout: 45_000 });
}

async function openExecutionStudioAnalytics(page: import("@playwright/test").Page): Promise<void> {
  await openExecutionStudioTab(page, "analytics");
  await expect(page.getByRole("button", { name: "Analytics", exact: true })).toHaveAttribute("aria-current", "page");
  const telemetry = page.locator("#execution-studio");
  await expect(telemetry.getByText("Tool runs", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(telemetry.getByText("Cost blocks", { exact: true })).toBeVisible({ timeout: 20_000 });
}

test.describe("Execution Studio tab", () => {
  test.setTimeout(120_000);

  test.beforeEach(async ({ context, baseURL, page }) => {
    test.skip(!executionStudioE2eEnabled, "Set E2E_EXECUTION_STUDIO=1 to run Execution Studio checks.");

    await clearIntegrationsSubnavPrefs(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);
    await installExecutionStudioApiMocks(page);
  });

  test("workspace shows telemetry and browser fallback controls", async ({ page }) => {
    await openExecutionStudioAnalytics(page);
    const telemetry = page.locator("#execution-studio");
    await expect(telemetry.getByText("Cost blocks", { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(telemetry.getByText("Per-connector activity")).toBeVisible({ timeout: 20_000 });
    await expect(telemetry.getByText("Connector activity chart")).toBeVisible({ timeout: 20_000 });
    await expect(telemetry.getByText("Activity over time (hourly)")).toBeVisible({ timeout: 20_000 });
    await expect(telemetry.getByText("2 runs")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: /Test browser fallback/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: /Confirm live browser step/i })).toBeVisible({ timeout: 20_000 });
    await expect(telemetry.getByText("Recent activity")).toBeVisible({ timeout: 20_000 });
  });

  test("manual tab loads sections", async ({ page }) => {
    await openExecutionStudioTab(page);
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

    await openExecutionStudioTab(page, "lanes");
    await expect(page.getByText("Pending SCV proposals")).toBeVisible({ timeout: 20_000 });
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

    await openExecutionStudioTab(page);
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

    await openExecutionStudioTab(page);
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

    await openExecutionStudioAnalytics(page);
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

    await openExecutionStudioTab(page);
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

    await openExecutionStudioAnalytics(page);
    await page.getByPlaceholder("ops@example.com, lead@example.com").fill("ops@queenswarm.love");
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

    await openExecutionStudioAnalytics(page);
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

    await openExecutionStudioAnalytics(page);
    await page.getByRole("button", { name: "Preview weekly digest" }).click();
    const preview = page.getByLabel("Weekly digest preview", { exact: true }).first();
    await expect(preview).toBeVisible({ timeout: 10_000 });
    await expect(preview.getByRole("button", { name: "Slack", exact: true })).toBeVisible();
    await expect(preview.getByText("Acme Hive")).toBeVisible();
  });

  test("send weekly digest preview posts send endpoint", async ({ page }) => {
    let sendCalled = false;

    await page.route("**/api/proxy/execution-studio/notifications/send-weekly-rollup-preview", async (route) => {
      sendCalled = route.request().method() === "POST";
      const body = route.request().postDataJSON() as { channels?: string[] };
      expect(body.channels).toEqual(["slack", "discord", "teams", "telegram"]);
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

    await openExecutionStudioAnalytics(page);
    await page.getByRole("button", { name: "Preview weekly digest" }).click();
    await expect(page.getByLabel("Weekly digest preview", { exact: true }).first()).toBeVisible({ timeout: 10_000 });
    await page.getByRole("button", { name: "Send weekly digest preview" }).click();
    await expect.poll(() => sendCalled).toBe(true);
  });
});
