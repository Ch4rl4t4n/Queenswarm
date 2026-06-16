import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics weekly routine (DA9)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("overview shows weekly routine KPI strip", async ({ page }) => {
    await page.goto("/apps-tools/analytics", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("analytics-routine-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Weekly leadership analytics deck")).toBeVisible();
    await expect(page.getByTestId("analytics-routine-panel").locator(".v4-badge", { hasText: "export ready" })).toBeVisible();
    await expect(page.getByTestId("analytics-routine-panel").locator(".v4-badge", { hasText: "scheduled" })).toBeVisible();
  });
});
