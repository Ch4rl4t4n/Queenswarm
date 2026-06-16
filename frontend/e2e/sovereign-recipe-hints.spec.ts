import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Sovereign recipe hints (LOC14)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("settings panel lists local-adapter imitation hints", async ({ page }) => {
    await page.goto("/settings/llm-keys", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const panel = page.getByTestId("sovereign-recipe-hints-panel");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel.getByText("Sovereign recipe hints · local-adapter")).toBeVisible();
    await expect(panel.getByText("Local sovereign ops routine")).toBeVisible();
    await expect(panel.locator(".font-mono").filter({ hasText: "83% success" })).toBeVisible();
  });
});
