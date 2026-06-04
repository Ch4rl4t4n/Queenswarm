import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { HIVE_PAGE_ZONE_SPECS } from "../lib/hive-page-zone-spec";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

test.describe("Whole-App performance — shell loading states", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  for (const spec of HIVE_PAGE_ZONE_SPECS) {
    test(`${spec.path} resolves HivePageShell after navigation`, async ({ page }) => {
      test.skip(
        !OPERATOR_CONTROL_PLANE_ENABLED && spec.path === "/agentic-os",
        "Agentic OS requires operator control plane",
      );

      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(spec.path, { waitUntil: "domcontentloaded", timeout: 60_000 });

      await expect(page.getByTestId("hive-page-shell")).toBeVisible({ timeout: 45_000 });
      await expect(page.getByTestId("hive-page-shell").locator("h1")).toHaveText(spec.title);
    });
  }

  test("apps-tools lazy index resolves module grid", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/apps-tools", { waitUntil: "domcontentloaded", timeout: 60_000 });

    await expect(page.getByTestId("hive-page-shell")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("heading", { name: "Apps & Tools", level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Module index" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Skill Factory", { exact: true })).toBeVisible({ timeout: 30_000 });
  });

  test("settings route exposes shell under progressive nav", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/security", { waitUntil: "domcontentloaded", timeout: 60_000 });

    await expect(page.getByTestId("hive-page-shell")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("navigation", { name: "Settings sections" })).toBeVisible({ timeout: 20_000 });
  });

  test("swarms page shows dismissible shell error banner on overview failure", async ({ page }) => {
    await page.route("**/api/proxy/dashboard/swarms-overview**", async (route) => {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Swarms overview unreachable" }),
      });
    });

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/swarms", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const shell = page.getByTestId("hive-page-shell");
    await expect(shell).toBeVisible({ timeout: 45_000 });

    const alert = shell.getByRole("alert");
    await expect(alert).toBeVisible({ timeout: 20_000 });
    await expect(alert).toContainText(/unreachable|502|failed/i);

    await shell.getByRole("button", { name: "Dismiss error" }).click();
    await expect(alert).not.toBeVisible();
  });

  test("agents page shows unified sync banner with retry on roster failure", async ({ page }) => {
    await page.route("**/api/proxy/agents?**", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Agents roster unreachable" }),
      });
    });

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/agents", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const shell = page.getByTestId("hive-page-shell");
    await expect(shell).toBeVisible({ timeout: 45_000 });

    const banner = shell.getByTestId("agents-sync-banner");
    await expect(banner).toBeVisible({ timeout: 20_000 });
    await expect(banner).toHaveAttribute("role", "alert");
    await expect(banner.getByRole("button", { name: "Retry sync" })).toBeVisible();
  });
});
