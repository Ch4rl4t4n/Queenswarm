import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const CONSOLIDATED_ROUTES: readonly string[] = ["/overview", "/agents", "/execution", "/knowledge", "/integrations", "/ballroom"];
const phase70NavE2eEnabled = process.env.E2E_PHASE70_NAV === "1";

test.describe("Phase 7.0 consolidated navigation", () => {
  test.use({ viewport: { width: 1366, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase70NavE2eEnabled, "Set E2E_PHASE70_NAV=1 to run Phase 7.0 consolidated navigation checks.");
  });

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("desktop sidebar renders consolidated top-level sections", async ({ page }) => {
    await page.goto("/overview", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("navigation", { name: "Hive navigation" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Agents" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Execution" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Knowledge" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Integrations" })).toBeVisible();
  });

  test("consolidated routes render shell canvas", async ({ page }) => {
    for (const route of CONSOLIDATED_ROUTES) {
      await page.goto(route, { waitUntil: "load", timeout: 60_000 });
      await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
      const pathname = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
      const normalizedTarget = route.replace(/\/$/, "") || "/";
      expect(pathname).toBe(normalizedTarget);
    }
  });
});
