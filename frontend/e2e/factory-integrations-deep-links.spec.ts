import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

/**
 * Deep-link hardening for Build (Skill Factory) + Integrations:
 *  - Legacy `/apps-tools/skill-factory#launch` (Launch tab removed) must land on
 *    the Library tab — previously a mount-time effect clobbered the hash to
 *    Research before it was read.
 *  - `/integrations#tools` must open the Connector hub tab and scroll to the
 *    real Tool Hub anchor (#hub-tools) — previously it fell through to Active.
 */
test.describe("Factory + Integrations deep links", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await suppressPwaInstallPrompt(page);
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("/apps-tools/skill-factory#launch lands on the Library tab", async ({ page }) => {
    await page.goto("/apps-tools/skill-factory#launch", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByTestId("hive-page-shell")).toBeVisible({ timeout: 30_000 });

    // Library tab content mounts (its DOM anchor) instead of defaulting to Research.
    await expect(page.locator("#skill-factory-library")).toBeAttached({ timeout: 20_000 });
  });

  test("/integrations#tools opens the Connector hub Tool Hub", async ({ page }) => {
    await page.goto("/integrations#tools", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Integrations", exact: true })).toBeVisible({ timeout: 30_000 });

    // Hub tab + Tool Hub anchor mount (previously fell through to the Active tab).
    await expect(page.locator("#hub-tools")).toBeAttached({ timeout: 20_000 });
  });
});
