import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";

test.describe("Whole-App Settings — progressive disclosure", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("essentials tier visible by default with advanced disclosure toggle", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/security", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const shell = page.getByTestId("hive-page-shell");
    await expect(shell).toBeVisible({ timeout: 45_000 });
    await expect(shell.locator("h1")).toHaveText("Settings");

    const subnav = page.locator(".settings-subnav-disclosure");
    await expect(subnav.getByRole("button", { name: "Show advanced settings" })).toBeVisible();
    await expect(subnav.getByRole("button", { name: /^Essentials\b/ })).toBeVisible();
    await expect(subnav.getByRole("button", { name: /^Advanced\b/ })).toHaveCount(0);
  });

  test("expanding advanced reveals operator and admin groups", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/security", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const subnav = page.locator(".settings-subnav-disclosure");
    await subnav.getByRole("button", { name: "Show advanced settings" }).click();
    await expect(subnav.getByRole("button", { name: /^Advanced\b/ })).toBeVisible();
    await expect(subnav.getByRole("button", { name: "Show fewer settings" })).toBeVisible();
  });

  test("deep link to harness auto-expands advanced tier", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/harness", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const subnav = page.locator(".settings-subnav-disclosure");
    await expect(subnav.getByRole("button", { name: /^Advanced\b/ })).toBeVisible({ timeout: 45_000 });
    await expect(subnav.getByRole("button", { name: "Show advanced settings" })).toHaveCount(0);
  });
});
