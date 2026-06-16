import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio settings (TJ4)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading journal page shows studio settings and routine strip", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=settings#journal-studio-settings", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-settings-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Studio settings" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Trading journal review" })).toBeVisible();
    await expect(page.getByTestId("journal-studio-routine-panel")).toContainText("scheduled", { timeout: 15_000 });
    await expect(page.getByText("Obsidian subfolder")).toBeVisible();
    await expect(page.getByText("fomo")).toBeVisible();
  });
});
