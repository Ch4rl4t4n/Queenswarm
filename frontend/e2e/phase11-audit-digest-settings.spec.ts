import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const phase11E2eEnabled = process.env.E2E_PHASE11_AUDIT_DIGEST === "1";

const defaultDigestConfig = {
  enabled: true,
  enabled_override: true,
  window_hours: 24,
  window_hours_override: null as number | null,
  schedule_hour_utc: 7,
  schedule_hour_override: null as number | null,
  extra_recipients: [] as string[],
  slack_webhook_configured: false,
  slack_webhook_preview: null as string | null,
  discord_webhook_configured: false,
  discord_webhook_preview: null as string | null,
  teams_webhook_configured: false,
  teams_webhook_preview: null as string | null,
  last_sent_at: null as string | null,
  global_enabled: true,
  global_window_hours: 24,
  global_schedule_hour_utc: 7,
};

test.describe("Phase 11 supervisor digest settings", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase11E2eEnabled, "Set E2E_PHASE11_AUDIT_DIGEST=1 to run Phase 11 digest settings checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    let digestConfig = { ...defaultDigestConfig };

    await page.route("**/api/proxy/settings/team/audit-logs", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });

    await page.route("**/api/proxy/settings/team/audit-digest/config", async (route) => {
      if (route.request().method() === "PATCH") {
        const patch = route.request().postDataJSON() as Record<string, unknown>;
        digestConfig = {
          ...digestConfig,
          enabled_override: typeof patch.enabled === "boolean" ? patch.enabled : digestConfig.enabled_override,
          window_hours: typeof patch.window_hours === "number" ? patch.window_hours : digestConfig.window_hours,
          schedule_hour_utc:
            typeof patch.schedule_hour_utc === "number" ? patch.schedule_hour_utc : digestConfig.schedule_hour_utc,
          extra_recipients: Array.isArray(patch.extra_recipients)
            ? (patch.extra_recipients as string[])
            : digestConfig.extra_recipients,
        };
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(digestConfig),
      });
    });

    await page.route("**/api/proxy/settings/team", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ members: [], invites: [] }),
      });
    });

    await page.route("**/api/proxy/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user-1",
          email: "owner@acme.com",
          tenant_role: "owner",
          permissions: ["*"],
          platform_features: { audit_settings: true, team_settings: true },
        }),
      });
    });
  });

  test("audit settings page shows digest schedule form and saves", async ({ page }) => {
    await page.goto("/settings/audit");

    await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
    await expect(page.getByText("Supervisor digest schedule")).toBeVisible();
    await expect(page.getByLabel("Window (hours)")).toBeVisible();
    await expect(page.getByText("Discord webhook override (optional)")).toBeVisible();
    await expect(page.getByRole("button", { name: "Test webhooks" })).toBeVisible();

    await page.getByLabel("Window (hours)").fill("12");
    await page.getByLabel("Extra recipients (one email per line)").fill("ops@acme.com");
    await page.getByRole("button", { name: "Save digest schedule" }).click();

    await expect(page.getByText("Supervisor digest schedule saved.", { exact: false })).toBeVisible();
  });
});
