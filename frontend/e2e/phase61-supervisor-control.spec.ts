import { expect, test, type Page } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const sessionId = "11111111-1111-4111-8111-111111111111";
const routineId = "22222222-2222-4222-8222-222222222222";
const phase61E2eEnabled = process.env.E2E_PHASE61_SUPERVISOR === "1";

const SESSIONS_LIST_RE = /\/api\/proxy\/agents\/sessions(\?limit=40)?$/;
const SESSIONS_SUMMARY_RE = /\/api\/proxy\/agents\/sessions\/summary$/;

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

async function dismissInteractDrawerIfOpen(page: Page): Promise<void> {
  const interactDrawer = page.getByPlaceholder("Ask sub-agents for a refinement, critique, or next step.");
  if (await interactDrawer.isVisible().catch(() => false)) {
    await page.keyboard.press("Escape");
    await expect(interactDrawer).not.toBeVisible({ timeout: 5_000 });
  }
}

async function dismissSessionDetailDrawerIfOpen(page: Page): Promise<void> {
  const closeBtn = page.locator(".fixed.inset-0.z-50").getByRole("button", { name: "Close" });
  if (await closeBtn.first().isVisible().catch(() => false)) {
    await closeBtn.first().click({ force: true });
  }
}

async function installSupervisorControlMocks(page: Page): Promise<{ setStatus: (status: string) => void }> {
  let currentStatus = "needs_input";

  await page.route(/\/api\/proxy\/agents(\?limit=120)?$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
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

  await page.route(SESSIONS_LIST_RE, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload(currentStatus)),
    });
  });

  await page.route(SESSIONS_SUMMARY_RE, async (route) => {
    const running = currentStatus === "running" ? 1 : 0;
    const needsInput = currentStatus === "needs_input" ? 1 : 0;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sessions_total: 1,
        status_counts: { [currentStatus]: 1 },
        running_sessions: running,
        needs_input_sessions: needsInput,
        completed_sessions: 0,
        routines_total: 1,
        active_routines: 1,
        due_routines: 1,
      }),
    });
  });

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/events(\\?limit=120)?$`), async (route) => {
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

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/review$`), async (route) => {
    const body = route.request().postDataJSON() as { decision?: string };
    currentStatus = body?.decision === "approve" ? "running" : "needs_input";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload(currentStatus)[0]),
    });
  });

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/control$`), async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sessionPayload(currentStatus)[0]),
    });
  });

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/shared-context$`), async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        enabled: true,
        matched_sections: ["policy"],
        sections: { policy: { rules: 2 } },
        retrieval_contract: "customer_history+policy+last_3_tasks",
        context_summary: sessionPayload(currentStatus)[0].context_summary,
        pruned_items: 0,
        prompt_block: null,
      }),
    });
  });

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/context-history`), async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route(new RegExp(`/api/proxy/agents/sessions/${sessionId}/audit-logs`), async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route(/\/api\/proxy\/agents\/routines(\?limit=40)?$/, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
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

  await page.route(/\/api\/proxy\/agents\/routines$/, async (route) => {
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

  await page.route(new RegExp(`/api/proxy/agents/routines/${routineId}/trigger$`), async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ session_id: sessionId }),
    });
  });

  return {
    setStatus: (status: string) => {
      currentStatus = status;
    },
  };
}

test.describe("Phase 6.1 supervisor control plane + routines", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.setTimeout(60_000);

  test.beforeEach(() => {
    test.skip(!phase61E2eEnabled, "Set E2E_PHASE61_SUPERVISOR=1 to run Phase 6.1 supervisor browser checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);
    await installSupervisorControlMocks(page);
  });

  test("review controls and routines interactions work from /agents", async ({ page }) => {
    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("navigation", { name: "Ecosystem shortcuts" })).toBeVisible({ timeout: 45_000 });

    if ((await page.getByText("Dynamic supervisor sessions").count()) === 0) {
      test.skip(true, "Dynamic supervisor panel is disabled in this environment.");
    }

    await expect(page.getByText("Dynamic supervisor sessions")).toBeVisible();
    await expect(page.getByText(/needs[_ ]input/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Approve" }).first()).toBeVisible({ timeout: 15_000 });

    await dismissSessionDetailDrawerIfOpen(page);
    await dismissInteractDrawerIfOpen(page);

    await page.getByRole("button", { name: "Approve" }).first().click({ force: true });
    await expect(page.getByText("running").first()).toBeVisible({ timeout: 15_000 });

    await dismissSessionDetailDrawerIfOpen(page);
    await dismissInteractDrawerIfOpen(page);

    await page.locator("#sessions .v4-routines-panel").getByPlaceholder("Routine name").fill("daily-monitoring");
    await page.locator("#sessions .v4-routines-panel").getByPlaceholder("Goal template").fill("Generate daily monitoring summary");
    await page.locator("#sessions .v4-routines-panel").getByRole("button", { name: "Create", exact: true }).click({ force: true });

    await expect(page.getByText(/daily-monitoring/i).first()).toBeVisible();
    await page.getByRole("button", { name: "Run now" }).first().click({ force: true });
  });
});

test.describe("Phase 6.1 supervisor create smoke", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(process.env.E2E_PHASE61_SUPERVISOR !== "1", "Set E2E_PHASE61_SUPERVISOR=1");
  });

  test("create session interact and approve flow", async ({ page, context, baseURL }) => {
    test.setTimeout(90_000);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);

    let currentStatus = "needs_input";
    let sessionCreated = false;
    const newSessionId = "44444444-4444-4444-8444-444444444444";
    const createdSession = () => ({
      ...sessionPayload(currentStatus)[0],
      id: newSessionId,
      goal: "Ship onboarding funnel audit",
    });

    await page.route(/\/api\/proxy\/agents\/sessions(\?limit=40)?$/, async (route) => {
      if (route.request().method() === "POST") {
        sessionCreated = true;
        currentStatus = "needs_input";
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(createdSession()),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sessionCreated ? [createdSession()] : []),
      });
    });

    await page.route(SESSIONS_SUMMARY_RE, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessions_total: 1,
          status_counts: { needs_input: 1 },
          running_sessions: 0,
          needs_input_sessions: 1,
          completed_sessions: 0,
          routines_total: 0,
          active_routines: 0,
          due_routines: 0,
        }),
      });
    });

    await page.route(/\/api\/proxy\/agents\/routines(\?limit=40)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/events`), async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/shared-context$`), async (route) => {
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
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/context-history`), async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/audit-logs`), async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/interact$`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "evt-interact-1",
          supervisor_session_id: newSessionId,
          event_type: "operator_interaction",
          level: "info",
          message: "Refine onboarding copy for EU users.",
          payload: {},
          occurred_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.route(new RegExp(`/api/proxy/agents/sessions/${newSessionId}/review$`), async (route) => {
      currentStatus = "running";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(createdSession()),
      });
    });

    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText("Dynamic supervisor sessions")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByPlaceholder("Session goal — e.g. investigate onboarding drop-off…")).toBeVisible({
      timeout: 15_000,
    });

    await dismissSessionDetailDrawerIfOpen(page);
    await dismissInteractDrawerIfOpen(page);
    await page.locator("#sessions").scrollIntoViewIfNeeded();

    const goalInput = page.locator("#sessions").getByPlaceholder("Session goal — e.g. investigate onboarding drop-off…");
    await expect(goalInput).toBeVisible({ timeout: 15_000 });
    await goalInput.fill("Ship onboarding funnel audit", { force: true });

    const createBtn = page.locator("#sessions").getByRole("button", { name: "Create session" });
    await expect(createBtn).toBeEnabled({ timeout: 15_000 });

    const createResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/proxy/agents/sessions") &&
        resp.request().method() === "POST" &&
        resp.status() === 201,
    );
    await createBtn.click({ force: true });
    await createResponse;

    await expect(page.getByText("Ship onboarding funnel audit")).toBeVisible({ timeout: 15_000 });

    const interactDrawer = page.getByPlaceholder("Ask sub-agents for a refinement, critique, or next step.");
    if (await interactDrawer.isVisible().catch(() => false)) {
      await interactDrawer.fill("Refine onboarding copy for EU users.");
      await page.getByRole("button", { name: "Send" }).click();
    }

    await dismissInteractDrawerIfOpen(page);

    await page.getByRole("button", { name: "Approve" }).first().click({ force: true });
    await expect(page.getByText("running").first()).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Phase 6.1 agents degraded states", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);
    await page.route(/\/api\/proxy\/agents(\?limit=120)?$/, async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "proxy_upstream_unreachable" }),
      });
    });
  });

  test("shows sync banner when agent roster fetch fails", async ({ page }) => {
    test.skip(process.env.E2E_PHASE61_SUPERVISOR !== "1", "Set E2E_PHASE61_SUPERVISOR=1");
    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    await expect(page.getByTestId("agents-sync-banner")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("button", { name: "Retry sync" })).toBeVisible();
  });
});
