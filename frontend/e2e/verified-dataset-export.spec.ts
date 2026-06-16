import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Verified dataset export (LOC5)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("settings panel shows export lane and download button", async ({ page }) => {
    const snapshotReady = page.waitForResponse(
      (res) => res.url().includes("llm-routing/verified-dataset") && res.status() === 200,
    );
    await page.goto("/settings/llm-keys", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await snapshotReady;
    const panel = page.getByTestId("verified-dataset-export-panel");
    await expect(panel).toBeVisible({ timeout: 15_000 });
    await expect(panel.getByText("Verified dataset export · Alpaca JSONL")).toBeVisible();
    await expect(panel.getByText("3 row(s) ready for Alpaca JSONL export.")).toBeVisible();
    await expect(panel.getByRole("button", { name: "Download JSONL" })).toBeEnabled();
  });
});
