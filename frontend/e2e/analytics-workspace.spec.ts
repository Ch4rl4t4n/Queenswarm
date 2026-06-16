import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics workspace (DA3)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("analytics workspace overview loads from snapshot", async ({ page }) => {
    await page.goto("/apps-tools/analytics", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("analytics-workspace-overview")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("apps.analytics.decision_report.v1")).toBeVisible();
  });
});
