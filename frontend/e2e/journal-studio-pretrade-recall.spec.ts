import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio pre-trade recall (TJ5)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading journal recall section shows mistakes and thesis strip", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=recall#journal-studio-pretrade-recall", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-pretrade-recall-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Pre-trade recall" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Top mistakes" })).toBeVisible();
    await expect(page.getByTestId("journal-studio-pretrade-recall-panel").getByText("fomo", { exact: true })).toBeVisible();
    await expect(page.getByTestId("journal-pretrade-thesis-strip")).toContainText("Kill if daily close");
  });
});
