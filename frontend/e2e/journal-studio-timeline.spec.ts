import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio timeline (TJ1)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading journal page shows timeline with merged entries", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=timeline#journal-studio-timeline", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-timeline-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Journal timeline" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent activity" })).toBeVisible();
    await expect(page.getByText("BUY BTC")).toBeVisible();
    await expect(page.getByText("FOMO re-entry")).toBeVisible();
    await expect(page.getByTestId("journal-studio-workspace-strip")).toBeVisible();
  });
});
