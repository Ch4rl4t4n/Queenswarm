import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio pattern strip (TJ6)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading journal patterns section shows win rates and repeat alerts", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=patterns#journal-studio-pattern-strip", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-pattern-strip-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "30/90-day pattern strip" })).toBeVisible();
    await expect(page.getByTestId("journal-pattern-repeat-alerts")).toBeVisible();
    await expect(page.getByTestId("journal-pattern-repeat-alerts").getByText("fomo", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "30-day window" })).toBeVisible();
  });
});
