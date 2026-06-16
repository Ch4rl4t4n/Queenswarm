import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Dataset recipe wizard (LOC6)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("settings panel shows local Q&A wizard controls", async ({ page }) => {
    await page.goto("/settings/llm-keys", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    const panel = page.getByTestId("dataset-recipe-wizard-panel");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel.getByText("Dataset Recipe wizard · local Q&A")).toBeVisible();
    await expect(panel.getByRole("button", { name: "Generate Q&A" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Approve all" })).toBeEnabled();
  });
});
