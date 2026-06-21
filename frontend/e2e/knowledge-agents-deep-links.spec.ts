import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

/**
 * Deep-link hardening: Knowledge reads `?tab=` (parity with Mission Control) and
 * Agents opens the Supervisor sub-section for `?session=`/`?preset=` links. These
 * are the producer hrefs (Mission Home, Jarvis, mocks) that previously landed on
 * the default tab.
 */
test.describe("Knowledge + Agents deep links", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await suppressPwaInstallPrompt(page);
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("/knowledge?tab=memory opens the Curated memory sub-section", async ({ page }) => {
    await page.goto("/knowledge?tab=memory", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible({ timeout: 30_000 });

    // The memory sub-section container only mounts when the Curated memory tab is active.
    await expect(page.locator("#memory")).toBeAttached({ timeout: 20_000 });
    await expect(page).toHaveURL(/tab=memory/);
  });

  test("/knowledge?tab=wiki opens the Wiki Layer sub-section", async ({ page }) => {
    await page.goto("/knowledge?tab=wiki", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("#wiki")).toBeAttached({ timeout: 20_000 });
  });

  test("/agents?preset=… opens the Supervisor sub-section", async ({ page }) => {
    await page.goto("/agents?preset=bank-po-brief", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Agents", exact: true })).toBeVisible({ timeout: 30_000 });

    // Supervisor sessions panel mounts (id="sessions") so the preset can be consumed.
    await expect(page.locator("#sessions").first()).toBeAttached({ timeout: 20_000 });
  });
});
