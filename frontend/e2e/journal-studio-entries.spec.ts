import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio trade entries (TJ2)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading journal entries section shows schema form and saved rows", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=entries#journal-studio-entries", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-entries-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Trade entries" })).toBeVisible();
    await expect(page.getByTestId("journal-entry-thesis")).toBeVisible();
    await expect(page.getByText("Breakout retest on BTC")).toBeVisible();
    await expect(page.getByText("Wait for confirmation candle")).toBeVisible();
  });
});
