import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics connector profile (DA7)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("connector profile panel shows GA4 active and configure CTAs", async ({ page }) => {
    await page.goto("/apps-tools/analytics?section=connectors#analytics-connectors", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByTestId("analytics-connector-profile")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-connector-ga4")).toBeVisible();
    await expect(page.getByText("GA4 Data API")).toBeVisible();
    await expect(page.getByText("property 123456789")).toBeVisible();
    await expect(page.getByTestId("analytics-connector-google_sheets")).toBeVisible();
  });
});
