import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics export lane (DA8)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("export lane shows preview and simulate submit", async ({ page }) => {
    const exportLaneReady = page.waitForResponse(
      (res) =>
        res.url().includes("analytics-workspace/export-lane") &&
        !res.url().includes("/preview") &&
        !res.url().includes("/submit") &&
        res.status() === 200,
    );
    await page.goto("/apps-tools/analytics", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("analytics-workspace-overview")).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: "Export inbox" }).click();
    await exportLaneReady;
    await expect(page.getByTestId("analytics-export-lane")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-export-preview")).toBeVisible();
    await expect(page.getByText("Signup funnel review")).toBeVisible();
    await expect(page.getByText("critic 4.5/5")).toBeVisible();
    await page.getByTestId("analytics-export-dest-slides").click();
    await expect(page.getByTestId("analytics-export-submit")).toBeEnabled();
    await page.getByTestId("analytics-export-submit").click();
    await expect(page.getByTestId("analytics-export-result")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Staged Google Slides deck/)).toBeVisible();
  });
});
