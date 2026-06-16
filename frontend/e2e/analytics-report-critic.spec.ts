import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics report critic (DA10)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("report critic shows score and run closed loop", async ({ page }) => {
    const criticReady = page.waitForResponse(
      (res) =>
        res.url().includes("analytics-workspace/report-critic") &&
        !res.url().includes("/run") &&
        res.status() === 200,
    );
    await page.goto("/apps-tools/analytics", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Report" }).click();
    await criticReady;
    await expect(page.getByTestId("analytics-report-critic")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-report-critic-score")).toContainText("critic 4.3/5");
    await expect(page.getByTestId("analytics-report-critic-export-ready")).toBeVisible();
    await page.getByTestId("analytics-report-critic-run").click();
    await expect(page.getByTestId("analytics-report-critic-result")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("analytics-report-critic-result")).toContainText("Critic PASS");
  });
});
