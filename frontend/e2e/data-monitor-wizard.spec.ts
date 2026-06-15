import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Data Monitor wizard (DG1)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("foragers page shows data monitor wizard with plan preview", async ({ page }) => {
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("data-monitor-wizard-panel")).toBeVisible({ timeout: 10_000 });
    const textarea = page.getByPlaceholder(/Track senior Python remote jobs/i);
    await textarea.fill("Track senior Python remote jobs in EU on public job boards");
    await page.waitForResponse(
      (res) => res.url().includes("data-monitor-wizard/preview") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByText("Jobs & hiring")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create monitor" })).toBeVisible();
  });
});
