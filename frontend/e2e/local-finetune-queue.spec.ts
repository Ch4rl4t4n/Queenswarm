import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Local fine-tune queue (LOC9)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("settings panel shows GPU fine-tune queue controls", async ({ page }) => {
    await page.goto("/settings/llm-keys", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const panel = page.getByTestId("local-finetune-queue-panel");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel.getByText("Fine-tune queue · GPU worker")).toBeVisible();
    await expect(panel.locator(".font-medium").filter({ hasText: "qs-v1" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Approve & enqueue" })).toBeVisible();
  });
});
