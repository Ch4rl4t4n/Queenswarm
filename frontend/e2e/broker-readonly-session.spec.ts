import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Broker read-only session (RA4)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading automation connect section loads readonly pack", async ({ page }) => {
    await page.goto("/apps-tools/trading-automation?section=connect#broker-readonly-session", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Automation" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Connect" }).click();
    await expect(page.getByText("Loading read-only broker session")).toBeVisible({ timeout: 5_000 }).catch(() => undefined);
    await expect(page.getByRole("heading", { name: "Read-only broker session" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: "Run smoke probe" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Start read-only session" })).toBeVisible();
  });
});
