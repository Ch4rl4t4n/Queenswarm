import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const sessionId = "11111111-1111-4111-8111-111111111111";
const routineId = "22222222-2222-4222-8222-222222222222";
const phase61E2eEnabled = process.env.E2E_PHASE61_SUPERVISOR === "1";

function sessionPayload(status: string) {
  return [
    {
      id: sessionId,
      goal: "Investigate checkout latency and propose safe fix",
      status,
      runtime_mode: "durable",
      created_by_subject: "dash:test",
      context_summary: {
        requested_roles: ["researcher", "critic"],
        retrieval_contract: "customer_history+policy+last_3_tasks",
      },
      swarm_id: null,
      task_id: null,
      started_at: new Date().toISOString(),
      completed_at: null,
      error_text: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      sub_agents: [
        {
          id: "31111111-1111-4111-8111-111111111111",
          role: "researcher",
          status: "running",
          runtime_mode: "durable",
          toolset: ["search", "read"],
          short_memory: {},
          spawn_order: 0,
          started_at: new Date().toISOString(),
          completed_at: null,
          last_output: "Research in progress",
          error_text: null,
        },
      ],
    },
  ];
}

test.describe("Phase 6.1 supervisor control plane + routines", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase61E2eEnabled, "Set E2E_PHASE61_SUPERVISOR=1 to run Phase 6.1 supervisor browser checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    let currentStatus = "needs_input";

    await page.route("**/api/proxy/agents?limit=120", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "a1111111-1111-4111-8111-111111111111",
            name: "Observer Bee",
            role: "researcher",
            status: "idle",
            pollen_points: 42,
          },
        ]),
      });
    });

    await page.route("**/api/proxy/agents/sessions?limit=40", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload(currentStatus)),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/events?limit=120`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "e1",
            supervisor_session_id: sessionId,
            sub_agent_session_id: null,
            event_type: "session_review",
            level: "info",
            message: "Session waiting for operator input.",
            payload: { decision: "reject" },
            occurred_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/review`, async (route) => {
      const body = route.request().postDataJSON() as { decision?: string };
      currentStatus = body?.decision === "approve" ? "running" : "needs_input";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload(currentStatus)[0]),
      });
    });

    await page.route(`**/api/proxy/agents/sessions/${sessionId}/control`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionPayload(currentStatus)[0]),
      });
    });

    await page.route("**/api/proxy/agents/routines?limit=40", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: routineId,
            name: "daily-monitoring",
            goal_template: "Generate daily monitoring summary",
            schedule_kind: "interval",
            interval_seconds: 3600,
            cron_expr: null,
            runtime_mode: "durable",
            roles: ["researcher", "critic"],
            retrieval_contract: "policy+last_3_tasks",
            skills: ["context", "diagnose"],
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
        ]),
      });
    });

    await page.route("**/api/proxy/agents/routines", async (route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "33333333-3333-4333-8333-333333333333",
          name: "daily-monitoring",
          goal_template: "Generate daily monitoring summary",
          schedule_kind: "interval",
          interval_seconds: 3600,
          cron_expr: null,
          runtime_mode: "durable",
          roles: ["researcher", "critic"],
          retrieval_contract: "policy+last_3_tasks",
          skills: ["context", "diagnose"],
          context_payload: {},
          status: "scheduled",
          is_active: true,
          created_by_subject: "dash:test",
          last_run_at: null,
          next_run_at: new Date().toISOString(),
          last_error: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
    });

    await page.route(`**/api/proxy/agents/routines/${routineId}/trigger`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ session_id: sessionId }),
      });
    });
  });

  test("review controls and routines interactions work from /agents", async ({ page }) => {
    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });

    await expect(page.getByText("Dynamic Supervisor Sessions")).toBeVisible();
    await expect(page.getByText("needs_input").first()).toBeVisible();

    await page.getByRole("button", { name: "Approve" }).first().click();
    await expect(page.getByText("running").first()).toBeVisible();

    await page.getByRole("button", { name: "Reject" }).first().click();
    await expect(page.getByText("needs_input").first()).toBeVisible();

    await page.getByPlaceholder("Routine name").fill("daily-monitoring");
    await page.getByPlaceholder("Goal template").fill("Generate daily monitoring summary");
    await page.getByRole("button", { name: "Create routine" }).click();

    await expect(page.getByText(/daily-monitoring/i).first()).toBeVisible();
    await page.getByRole("button", { name: "Run now" }).first().click();
  });
});
