import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";

test.describe("Agents page — navigation clicks", () => {
  test.beforeEach(async ({ page }) => {
    await maybeInstallShellApiMocks(page);
  });

  test("desktop sidebar, hub strip, spawn, and subnav all navigate", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    await page.goto("/agents", { waitUntil: "domcontentloaded", timeout: 60_000 });
    if (page.url().includes("/login")) {
      test.skip(true, "No dashboard session — skip click smoke");
    }

    await expect(page.getByRole("heading", { name: "Agents", exact: true })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("navigation", { name: "Agents ecosystem sections" }).getByRole("button", { name: "Hybrid runtime" }).click();
    await expect(page).toHaveURL(/\/agents(#runtime|$)/);
    await expect(page.getByRole("heading", { name: "Hybrid runtime" })).toBeVisible({ timeout: 15_000 });

    await page.goto("/agents", { waitUntil: "domcontentloaded" });
    await page.locator("#agents-ecosystem").getByRole("link", { name: "Integrations" }).click();
    await expect(page).toHaveURL(/\/integrations/, { timeout: 15_000 });

    await page.goto("/agents", { waitUntil: "domcontentloaded" });
    await page.getByRole("link", { name: "Spawn agent" }).first().click();
    await expect(page).toHaveURL(/\/agents\/new/, { timeout: 15_000 });

    await page.goto("/agents", { waitUntil: "domcontentloaded" });
    await page.locator(".hive-sidebar-rail--desktop").getByRole("link", { name: "Tasks" }).click();
    await expect(page).toHaveURL(/\/tasks/, { timeout: 15_000 });
  });
});
