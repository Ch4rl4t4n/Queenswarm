import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

/**
 * Regression for "Do this does nothing": operator CTAs navigate to `#anchor`
 * deep links. The shell-mounted useRouteHashScroll must land on (and reveal)
 * the target even when it renders below the fold after async panels mount.
 */
test.describe("Deep-link hash scroll (Do this lands)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await suppressPwaInstallPrompt(page);
  });

  test("mobile · #mission-step-verify scrolls into view", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/tasks#mission-step-verify", { waitUntil: "load", timeout: 60_000 });

    await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({
      timeout: 30_000,
    });

    const verify = page.locator("#mission-step-verify");
    await expect(verify).toBeVisible({ timeout: 20_000 });
    // The target sits below the fold on mobile; the hook must reveal it.
    await expect(verify).toBeInViewport({ timeout: 8_000 });
  });
});
