import { expect, test } from "@playwright/test";

import { seedDashboardAccessToken } from "./fixtures/dashboard-session";

/**
 * Opt-in authenticated staging — real supervisor + Execution Studio APIs.
 * Requires: E2E_EXECUTION_STUDIO_STAGING=1, PLAYWRIGHT_BASE_URL, OPERATOR_USER_BEARER_TOKEN.
 */
const stagingEnabled = process.env.E2E_EXECUTION_STUDIO_STAGING === "1";
const baseConfigured = !!(process.env.PLAYWRIGHT_BASE_URL?.trim());
const accessToken = process.env.OPERATOR_USER_BEARER_TOKEN?.trim() ?? "";

test.describe("Execution Studio staging API", () => {
  test.skip(!stagingEnabled || !baseConfigured, "Set E2E_EXECUTION_STUDIO_STAGING=1 and PLAYWRIGHT_BASE_URL.");

  test("pending-approvals endpoint returns structured snapshot", async ({ request, baseURL }) => {
    const origin = baseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "";
    const resp = await request.get(`${origin}/api/proxy/execution-studio/pending-approvals`, {
      failOnStatusCode: false,
    });
    expect([200, 401, 403]).toContain(resp.status());
    if (resp.status() === 200) {
      const body = (await resp.json()) as { count?: number; live_actions?: unknown[] };
      expect(typeof body.count).toBe("number");
      expect(Array.isArray(body.live_actions)).toBe(true);
    }
  });

  test("overview includes pending_approvals and activity_time_series keys", async ({ request, baseURL }) => {
    const origin = baseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "";
    const resp = await request.get(`${origin}/api/proxy/execution-studio/overview`, {
      failOnStatusCode: false,
    });
    expect([200, 401, 403]).toContain(resp.status());
    if (resp.status() === 200) {
      const body = (await resp.json()) as {
        pending_approvals?: { count?: number };
        activity_telemetry?: { activity_time_series?: unknown[] };
        notifications?: { email_recipients?: string[] };
      };
      expect(body.pending_approvals).toBeTruthy();
      expect(Array.isArray(body.activity_telemetry?.activity_time_series)).toBe(true);
      expect(Array.isArray(body.notifications?.email_recipients)).toBe(true);
    }
  });

  test("supervisor sessions list endpoint is reachable", async ({ request, baseURL }) => {
    const origin = baseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "";
    const resp = await request.get(`${origin}/api/proxy/agents/sessions?limit=5`, {
      failOnStatusCode: false,
    });
    expect([200, 401, 403]).toContain(resp.status());
    if (resp.status() === 200) {
      const body = await resp.json();
      expect(Array.isArray(body)).toBe(true);
    }
  });
});

test.describe("Execution Studio authenticated staging", () => {
  test.skip(
    !stagingEnabled || !baseConfigured || !accessToken,
    "Set E2E_EXECUTION_STUDIO_STAGING=1, PLAYWRIGHT_BASE_URL, OPERATOR_USER_BEARER_TOKEN.",
  );

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardAccessToken(context, baseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "", accessToken);
  });

  test("supervisor sessions and Execution Studio overview load with bearer token", async ({ page, baseURL }) => {
    const origin = baseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "";
    const overviewResp = await page.request.get(`${origin}/api/proxy/execution-studio/overview`);
    expect([200, 403]).toContain(overviewResp.status());
    if (overviewResp.status() === 200) {
      const body = (await overviewResp.json()) as { enabled?: boolean; notifications?: { email_recipients?: string[] } };
      expect(body.enabled).toBe(true);
      expect(Array.isArray(body.notifications?.email_recipients)).toBe(true);
    }

    const sessionsResp = await page.request.get(`${origin}/api/proxy/agents/sessions?limit=3`);
    expect([200, 403]).toContain(sessionsResp.status());
    if (sessionsResp.status() === 200) {
      const sessions = (await sessionsResp.json()) as unknown[];
      expect(Array.isArray(sessions)).toBe(true);
    }
  });
});
