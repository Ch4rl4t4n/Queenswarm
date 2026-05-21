import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const phase14E2eEnabled = process.env.E2E_PHASE14_OPERATOR_FLOWS === "1";
const sessionId = "88888888-8888-4888-8888-888888888888";
const recipeId = "99999999-9999-4999-8999-999999999999";

const defaultPlaybookConfig = {
  auto_save_on_approve: false,
  auto_save_on_approve_override: null as boolean | null,
  mark_verified_on_auto_save: true,
  mark_verified_on_auto_save_override: null as boolean | null,
  recipes_enabled: true,
};

const internalAdminMe = {
  id: "user-admin",
  email: "admin@acme.com",
  display_name: "Admin Operator",
  twofa_enabled: false,
  twofa_pending: false,
  backup_codes_remaining: 0,
  is_admin: true,
  platform_mode: "internal",
  subscription_tier: "pro",
  platform_features: {},
  scopes: ["dash:admin", "dash:operator", "dash:read", "dash:recipe_write"],
};

const commandCenterSnapshotStub = {
  generated_at: new Date().toISOString(),
  instance_id: "playwright-command-center",
  host: {
    cpu_percent: 12,
    memory_percent: 40,
    disk_percent: 22,
    memory_used_gb: 6.4,
    memory_total_gb: 16,
    disk_used_gb: 120,
    disk_total_gb: 512,
    swap_percent: 4,
    resource_pressure: false,
    resource_pressure_reason: "",
  },
  dependencies: [],
  llm_providers: [],
  integrations: [],
  hive_load: {
    agents_total: 1,
    agents_running: 0,
    tasks_running: 0,
    tasks_pending: 0,
    simulation_tasks_running: 0,
    simulation_tasks_pending: 0,
    llm_in_flight: 0,
    llm_concurrency_limit: 4,
    simulation_in_flight: 0,
    simulation_concurrency_limit: 2,
    simulations_enabled: true,
  },
  docker: { available: false, running_total: null, queenswarm_running: null, containers: [] },
  host_history: [],
  telemetry: { rate_limit_blocks_5m: 0, scaling_events_5m: 0 },
  summary: {
    dependencies_ok: true,
    llm_routes_ok: true,
    integrations_ok: true,
  },
};

function sessionRow(contextSummary: Record<string, unknown> = {}, status = "needs_input") {
  return {
    id: sessionId,
    goal: "Ship operator playbook from verified supervisor session",
    status,
    runtime_mode: "durable",
    created_by_subject: "dash:test",
    context_summary: {
      requested_roles: ["researcher", "critic"],
      retrieval_contract: "customer_history+policy+last_3_tasks",
      ...contextSummary,
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
        id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        role: "researcher",
        status: "completed",
        runtime_mode: "durable",
        toolset: ["search"],
        short_memory: {},
        spawn_order: 0,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        last_output: "Collected pricing constraints and competitor notes.",
        error_text: null,
      },
      {
        id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        role: "critic",
        status: "completed",
        runtime_mode: "durable",
        toolset: ["review"],
        short_memory: {},
        spawn_order: 1,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        last_output: "Validated guardrails and flagged one regression risk.",
        error_text: null,
      },
    ],
  };
}

async function seedAgentsApiMocks(
  page: import("@playwright/test").Page,
  options?: {
    contextSummary?: Record<string, unknown>;
    onReview?: (decision: string) => Record<string, unknown>;
  },
) {
  let currentSession = sessionRow(options?.contextSummary ?? {});

  await page.route("**/api/proxy/agents?limit=120", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  // Single handler registered last so it wins over shell-api-mocks `agents/sessions` stubs.
  await page.route((url) => {
    const href = url.href;
    return href.includes("/api/proxy/agents/sessions") && !href.includes("/api/proxy/agents/browser-sessions");
  }, async (route) => {
    const url = new URL(route.request().url());
    const tail = url.pathname.replace(/^\/api\/proxy\/agents\/sessions\/?/, "");
    const method = route.request().method();

    if (!tail && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([currentSession]),
      });
      return;
    }

    if (tail === "summary" && method === "GET") {
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
      return;
    }

    if (tail === `${sessionId}/events` && url.search.includes("limit=120") && method === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (tail === `${sessionId}/shared-context` && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: sessionId,
          enabled: false,
          retrieval_contract: "",
          matched_sections: [],
          sections: {},
          pruned_items: 0,
          prompt_block: "",
          context_summary: {},
        }),
      });
      return;
    }

    if (tail === `${sessionId}/context-history` && url.search.includes("limit=8") && method === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (tail === `${sessionId}/audit-logs` && url.search.includes("limit=12") && method === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }

    if (tail.startsWith(`${sessionId}/sub-agents/`) && tail.endsWith("/job") && method === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "idle" }) });
      return;
    }

    if (tail === `${sessionId}/playbook/preview` && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: sessionId,
          suggested_name: "playbook_ship_operator_playbook_abc123",
          step_count: 3,
          can_mark_verified: true,
          session_status: currentSession.status,
          sub_agent_count: 2,
        }),
      });
      return;
    }

    if (tail === `${sessionId}/playbook` && method === "POST") {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          recipe_id: recipeId,
          name: "playbook_ship_operator_playbook_abc123",
          step_count: 3,
          verified: true,
          can_mark_verified: true,
        }),
      });
      return;
    }

    if (tail === `${sessionId}/review` && method === "POST") {
      const body = route.request().postDataJSON() as { decision?: string };
      const decision = body?.decision ?? "approve";
      const extra =
        options?.onReview?.(decision) ??
        (decision === "approve"
          ? {
              playbook_recipe_id: recipeId,
              playbook_auto_saved_at: new Date().toISOString(),
            }
          : {});
      currentSession = sessionRow(extra, decision === "approve" ? "running" : "needs_input");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(currentSession),
      });
      return;
    }

    await route.fallback();
  });

  await page.route(/\/api\/proxy\/agents\/browser-sessions/, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route(/\/api\/proxy\/agents\/routines/, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route(/\/api\/proxy\/agents\/suggestions/, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route(/\/api\/proxy\/hive-mind\/memory-evolution\/proposals/, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
}

test.describe("Phase 14 operator digest + playbook flows", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase14E2eEnabled, "Set E2E_PHASE14_OPERATOR_FLOWS=1 to run Phase 14 operator flow checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);

    await page.route("**/api/proxy/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(internalAdminMe),
      });
    });
  });

  test("audit settings saves session playbook automation", async ({ page }) => {
    let playbookConfig = { ...defaultPlaybookConfig };

    await page.route("**/api/proxy/settings/team/audit-logs", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await page.route("**/api/proxy/settings/team/audit-digest/config", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          enabled_override: true,
          window_hours: 24,
          window_hours_override: null,
          schedule_hour_utc: 7,
          schedule_hour_override: null,
          extra_recipients: [],
          slack_webhook_configured: false,
          slack_webhook_preview: null,
          discord_webhook_configured: false,
          discord_webhook_preview: null,
          teams_webhook_configured: false,
          teams_webhook_preview: null,
          last_sent_at: null,
          global_enabled: true,
          global_window_hours: 24,
          global_schedule_hour_utc: 7,
        }),
      });
    });

    await page.route("**/api/proxy/settings/team/session-playbook/config", async (route) => {
      if (route.request().method() === "PATCH") {
        const patch = route.request().postDataJSON() as Record<string, unknown>;
        playbookConfig = {
          ...playbookConfig,
          auto_save_on_approve_override:
            typeof patch.auto_save_on_approve === "boolean" ? patch.auto_save_on_approve : playbookConfig.auto_save_on_approve_override,
          mark_verified_on_auto_save_override:
            typeof patch.mark_verified_on_auto_save === "boolean"
              ? patch.mark_verified_on_auto_save
              : playbookConfig.mark_verified_on_auto_save_override,
          auto_save_on_approve:
            typeof patch.auto_save_on_approve === "boolean" ? patch.auto_save_on_approve : playbookConfig.auto_save_on_approve,
        };
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...playbookConfig,
          auto_save_on_approve: playbookConfig.auto_save_on_approve_override ?? playbookConfig.auto_save_on_approve,
          mark_verified_on_auto_save:
            playbookConfig.mark_verified_on_auto_save_override ?? playbookConfig.mark_verified_on_auto_save,
        }),
      });
    });

    await page.route("**/api/proxy/settings/team", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ members: [], invites: [] }),
      });
    });

    await page.goto("/settings/audit");
    await expect(page.getByRole("heading", { name: "Session playbook automation" }).first()).toBeVisible();
    await page.getByLabel("Auto-save playbook on session approve").click();
    await page.getByRole("option", { name: "Enabled for this tenant" }).click();
    await page.getByRole("button", { name: "Save playbook automation" }).click();
    await expect(page.getByText("Session playbook automation saved.", { exact: false })).toBeVisible();
  });

  test("agents drawer saves operator playbook via preview modal", async ({ page }) => {
    test.setTimeout(90_000);
    await seedAgentsApiMocks(page);

    const sessionsReady = page.waitForResponse(
      (response) =>
        response.url().includes("/api/proxy/agents/sessions") &&
        response.url().includes("limit=40") &&
        response.status() === 200,
    );

    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    const sessionsResponse = await sessionsReady;
    const sessionsPayload: unknown = await sessionsResponse.json();
    expect(Array.isArray(sessionsPayload)).toBeTruthy();

    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });

    await expect(page.getByText("Dynamic supervisor sessions")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Session detail")).toBeVisible({ timeout: 10_000 });
    const drawer = page.locator("div.fixed.inset-0").filter({ hasText: "Session detail" });
    await drawer.getByRole("button", { name: "Save playbook" }).click();
    const dialog = page.getByRole("dialog", { name: "Save operator playbook" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("3 steps")).toBeVisible();
    await dialog.getByRole("button", { name: "Save playbook" }).click();
    await expect(page.getByText("Playbook saved", { exact: false })).toBeVisible();
  });

  test("agents approve shows auto-saved playbook toast with recipes link", async ({ page }) => {
    test.setTimeout(90_000);
    await seedAgentsApiMocks(page);

    const sessionsReady = page.waitForResponse(
      (response) =>
        response.url().includes("/api/proxy/agents/sessions") &&
        response.url().includes("limit=40") &&
        response.status() === 200,
    );

    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    const sessionsResponse = await sessionsReady;
    const sessionsPayload: unknown = await sessionsResponse.json();
    expect(Array.isArray(sessionsPayload)).toBeTruthy();

    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });

    await expect(page.getByText("Dynamic supervisor sessions")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Session detail")).toBeVisible({ timeout: 10_000 });
    const drawer = page.locator("div.fixed.inset-0").filter({ hasText: "Session detail" });
    await drawer.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText("operator playbook auto-saved", { exact: false })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open recipes" })).toBeVisible();
    await expect(page.locator(".v4-session-row").getByRole("link", { name: "playbook" })).toBeVisible();
  });

  test("command center rollup shows cached snapshot label", async ({ page }) => {
    await page.route("**/api/proxy/operator/command-center", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(commandCenterSnapshotStub),
      });
    });

    await page.route(/\/api\/proxy\/operator\/command-center\/audit-digest-rollup\?window_hours=168$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          window_hours: 168,
          generated_at: new Date().toISOString(),
          tenants_active: 2,
          tenants_total: 3,
          total_actions: 14,
          global_action_counts: { supervisor_session_control: 8, supervisor_session_review: 6 },
          daily_trend: [
            { date: "2026-05-13", action_count: 0, tenants_active: 0 },
            { date: "2026-05-14", action_count: 4, tenants_active: 1 },
            { date: "2026-05-15", action_count: 6, tenants_active: 2 },
            { date: "2026-05-16", action_count: 2, tenants_active: 1 },
            { date: "2026-05-17", action_count: 1, tenants_active: 1 },
            { date: "2026-05-18", action_count: 1, tenants_active: 1 },
            { date: "2026-05-19", action_count: 0, tenants_active: 0 },
          ],
          tenants: [
            {
              tenant_id: "88888888-8888-4888-8888-888888888888",
              tenant_name: "Acme Hive",
              tenant_slug: "acme",
              platform_mode: "internal",
              action_count: 10,
              session_count: 4,
              action_counts: { supervisor_session_control: 6 },
              digest_enabled: true,
              digest_health: "never_sent",
              last_digest_sent_at: null,
            },
          ],
          digest_health_summary: { never_sent: 1 },
          cached: true,
        }),
      });
    });

    await page.route(
      "**/api/proxy/operator/command-center/audit-digest-rollup/tenants/*/send-digest*",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            tenant_id: "88888888-8888-4888-8888-888888888888",
            sent: true,
            sent_count: 1,
            action_count: 10,
          }),
        });
      },
    );

    await page.route(
      "**/api/proxy/operator/command-center/audit-digest-rollup/send-attention-digests*",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            sent: true,
            tenants_attempted: 1,
            tenants_sent: 1,
            digest_stale_count: 0,
            digest_never_sent_count: 1,
          }),
        });
      },
    );

    await page.goto("/settings/command-center");
    await expect(page.getByRole("heading", { name: "Command center" })).toBeVisible();
    await expect(page.getByText("Supervisor audit rollup")).toBeVisible();
    await expect(page.getByText("cached snapshot")).toBeVisible();
    await expect(page.getByText("1 never sent")).toBeVisible();
    await expect(page.locator("table").getByText("Never sent", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Send digest" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Send all alerts" })).toBeVisible();
    await page.getByRole("button", { name: "Send digest" }).click();
    await expect(page.getByText("Digest sent for Acme Hive", { exact: false })).toBeVisible();
    await page.getByRole("button", { name: "Send all alerts" }).click();
    await expect(page.getByText("Digests sent for 1/1 alert hives", { exact: false })).toBeVisible();
    await expect(page.getByText("7-day operator trend")).toBeVisible();
  });
});
