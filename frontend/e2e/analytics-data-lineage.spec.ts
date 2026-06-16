import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics data lineage (DA6)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("lineage strip renders verified rows from snapshot", async ({ page }) => {
    await page.goto("/apps-tools/analytics?section=lineage#analytics-lineage", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByTestId("analytics-data-lineage")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Signup funnel review")).toBeVisible();
    await expect(page.getByTestId("analytics-lineage-row-kpi-wau")).toBeVisible();
    await expect(page.getByText("GA4 Data API")).toBeVisible();
    await expect(page.getByText("1 verified")).toBeVisible();
  });
});
