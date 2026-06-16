import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Broker guardrails (RA3)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading automation guardrails section loads broker pack", async ({ page }) => {
    await page.goto("/apps-tools/trading-automation?section=guardrails#broker-guardrails", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Automation" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Broker guardrails" }).click();
    await expect(page.getByText("Loading broker guardrails")).toBeVisible({ timeout: 5_000 }).catch(() => undefined);
    await expect(page.getByRole("heading", { name: "Broker guardrails" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Max order (USD)")).toBeVisible();
    await expect(page.getByText("Daily cap (USD)")).toBeVisible();
    await expect(page.getByText("polymarket", { exact: true })).toBeVisible();
  });
});
