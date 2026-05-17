import { expect, test, type Page } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const CORE_ROUTES: ReadonlyArray<{ route: string; acceptedPathnames: readonly string[] }> = [
  { route: "/dashboard", acceptedPathnames: ["/dashboard", "/"] },
  { route: "/agents", acceptedPathnames: ["/agents"] },
  { route: "/tasks", acceptedPathnames: ["/tasks"] },
  { route: "/knowledge", acceptedPathnames: ["/knowledge", "/hive-mind"] },
  { route: "/integrations", acceptedPathnames: ["/integrations", "/connectors"] },
  { route: "/ballroom", acceptedPathnames: ["/ballroom"] },
];
const ALIAS_REDIRECT_ROUTES: ReadonlyArray<{ from: string; acceptedPathnames: readonly string[] }> = [
  { from: "/overview", acceptedPathnames: ["/overview", "/dashboard", "/"] },
  { from: "/execution", acceptedPathnames: ["/execution", "/tasks", "/dashboard"] },
  { from: "/hive-mind", acceptedPathnames: ["/hive-mind", "/knowledge"] },
  { from: "/outputs", acceptedPathnames: ["/outputs", "/knowledge"] },
  { from: "/learning", acceptedPathnames: ["/learning", "/knowledge"] },
  { from: "/recipes", acceptedPathnames: ["/recipes", "/knowledge"] },
  { from: "/connectors", acceptedPathnames: ["/connectors", "/integrations"] },
  { from: "/external-projects", acceptedPathnames: ["/external-projects", "/integrations"] },
  { from: "/plugins", acceptedPathnames: ["/plugins", "/integrations"] },
  { from: "/hierarchy", acceptedPathnames: ["/hierarchy", "/agents"] },
];
const phase70NavE2eEnabled = process.env.E2E_PHASE70_NAV === "1";

async function gotoWithRedirectTolerance(page: Page, route: string): Promise<void> {
  try {
    await page.goto(route, { waitUntil: "domcontentloaded", timeout: 60_000 });
  } catch (error) {
    if (!(error instanceof Error) || !error.message.includes("ERR_ABORTED")) {
      throw error;
    }
    await page.goto(route, { waitUntil: "load", timeout: 60_000 });
  }
  await page.waitForLoadState("load", { timeout: 60_000 });
}

test.describe("Phase 7.0 consolidated navigation", () => {
  test.use({ viewport: { width: 1366, height: 900 } });

  test.beforeEach(() => {
    test.skip(!phase70NavE2eEnabled, "Set E2E_PHASE70_NAV=1 to run Phase 7.0 consolidated navigation checks.");
  });

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("desktop sidebar renders top-level sections", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "load", timeout: 60_000 });
    const nav = page.getByRole("navigation", { name: "Hive navigation" });
    await expect(nav).toBeVisible({ timeout: 30_000 });
    await expect(nav.getByRole("link", { name: "Dashboard", exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Agents", exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Tasks", exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Knowledge", exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Integrations", exact: true })).toBeVisible();
  });

  test("core routes render shell canvas", async ({ page }) => {
    for (const { route, acceptedPathnames } of CORE_ROUTES) {
      await gotoWithRedirectTolerance(page, route);
      const current = new URL(page.url());
      const pathname = current.pathname.replace(/\/$/, "") || "/";
      if (pathname === "/login") {
        expect(current.searchParams.get("next")).toBe(route);
        continue;
      }
      await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
      expect(acceptedPathnames).toContain(pathname);
    }
  });

  test("legacy aliases remain backward-compatible", async ({ page }) => {
    for (const { from, acceptedPathnames } of ALIAS_REDIRECT_ROUTES) {
      await gotoWithRedirectTolerance(page, from);
      const current = new URL(page.url());
      const pathname = current.pathname.replace(/\/$/, "") || "/";
      if (pathname === "/login") {
        const nextTarget = current.searchParams.get("next");
        expect([from, ...acceptedPathnames]).toContain(nextTarget);
        continue;
      }
      await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
      expect(acceptedPathnames).toContain(pathname);
    }
  });

  test("mobile shell exposes sticky header and bottom nav", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("banner").first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeVisible({
      timeout: 30_000,
    });
    await expect(
      page.getByRole("navigation", { name: "Primary mobile navigation" }).getByRole("link", { name: "Ballroom" }),
    ).toBeVisible();
  });
});
