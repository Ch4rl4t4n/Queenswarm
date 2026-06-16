import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Local adapter registry (LOC8)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("settings panel lists registered adapter", async ({ page }) => {
    await page.goto("/settings/llm-keys", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const panel = page.getByTestId("local-adapter-registry-panel");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel.getByText("Local adapter registry")).toBeVisible();
    await expect(panel.locator(".font-mono").filter({ hasText: "ollama/queenswarm-v1" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Register adapter" })).toBeVisible();
  });
});
