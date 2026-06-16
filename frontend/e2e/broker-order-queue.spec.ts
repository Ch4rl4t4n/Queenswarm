import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Broker order queue (RA5)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading automation orders section loads HITL queue", async ({ page }) => {
    await page.goto("/apps-tools/trading-automation?section=orders#broker-order-queue", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Automation" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Order queue" }).click();
    await expect(page.getByText("Loading broker order queue")).toBeVisible({ timeout: 5_000 }).catch(() => undefined);
    await expect(page.getByRole("heading", { name: "HITL order queue" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Buy YES token-1")).toBeVisible();
    await expect(page.getByRole("button", { name: "Approve & execute" })).toBeVisible();
  });
});
