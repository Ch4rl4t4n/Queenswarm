import { expect, test } from "@playwright/test";

import { seedDashboardAccessToken } from "./fixtures/dashboard-session";

const enabled = process.env.E2E_PROD_AUTHENTICATED === "1";
const accessToken = process.env.OPERATOR_USER_BEARER_TOKEN?.trim() ?? "";

async function gotoShellRoute(page: import("@playwright/test").Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 90_000 });
  const currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
  expect(currentPath, `expected shell route ${path}, got ${currentPath}`).not.toBe("/login");
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 60_000 });
}

test.describe("Prod authenticated walkthrough", () => {
  test.skip(!enabled || !accessToken, "Set E2E_PROD_AUTHENTICATED=1 and OPERATOR_USER_BEARER_TOKEN.");

  test.beforeEach(async ({ page, context, baseURL }) => {
    await seedDashboardAccessToken(context, baseURL ?? "https://queenswarm.love", accessToken);
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("dashboard shell loads without duplicate top search bar", async ({ page }) => {
    await gotoShellRoute(page, "/");
    await expect(page.locator("#hive-search")).toHaveCount(0);
    await expect(page.locator('[data-hive-shell="canvas"]')).toBeVisible({ timeout: 45_000 });
  });

  test("core hubs reachable from shell", async ({ page }) => {
    for (const path of ["/agents", "/integrations", "/tasks", "/knowledge", "/ballroom"]) {
      await gotoShellRoute(page, path);
    }
  });

  test("swarm builder templates load", async ({ page }) => {
    for (const query of ["", "?template=exec-assistant", "?template=lead-waterfall", "?template=content-flywheel"]) {
      await gotoShellRoute(page, `/swarms/new${query}`);
      await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 45_000 });
    }
  });

  test("costs billing and enterprise settings shells load", async ({ page }) => {
    await gotoShellRoute(page, "/settings/costs");
    await expect(page.getByText(/plan|billing|tier|costs/i).first()).toBeVisible({ timeout: 45_000 });

    await gotoShellRoute(page, "/settings/enterprise");
    await expect(page.getByText(/enterprise|white-label|compliance|HA/i).first()).toBeVisible({ timeout: 45_000 });

    await gotoShellRoute(page, "/settings/capabilities");
    await expect(page.getByText(/capabilities|atlas/i).first()).toBeVisible({ timeout: 45_000 });
  });

  test("AI harness operator hub loads on prod", async ({ page }) => {
    await gotoShellRoute(page, "/settings/harness");
    const hub = page.locator("#operator-hub");
    await expect(hub).toBeVisible({ timeout: 60_000 });
    await expect(hub.getByRole("heading", { name: /Autonomy & live lane hub/i })).toBeVisible();
    await expect(hub.getByText("Next action")).toBeVisible();
    await expect(hub.getByText("Social OAuth readiness")).toBeVisible();
  });

  test("Four Cs readiness audit loads on prod harness rules overview", async ({ page }) => {
    await gotoShellRoute(page, "/settings/harness#rules");
    await expect(page.getByRole("heading", { name: /Four Cs readiness/i })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Context/i).first()).toBeVisible();
    await expect(page.getByText(/Manual → Four Cs/i)).toBeVisible();
  });

  test("Innovation Lab shell loads on prod cockpit", async ({ page }) => {
    await gotoShellRoute(page, "/agentic-os#innovation");
    await expect(page.getByRole("heading", { name: /Brainstorm → approve/i })).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByPlaceholder(/Telegram inbound/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Manual → Viability gate/i })).toBeVisible();
  });

  test("agents sessions tab shell loads", async ({ page }) => {
    await gotoShellRoute(page, "/agents");
    const sessionsTab = page.getByRole("tab", { name: /sessions/i }).or(page.getByRole("link", { name: /sessions/i }));
    if (await sessionsTab.count()) {
      await sessionsTab.first().click();
    }
    await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });
  });
});
