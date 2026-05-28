import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { HIVE_PAGE_ZONE_SPECS } from "../lib/hive-page-zone-spec";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

test.describe("Whole-App page shell — zone headers", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  for (const spec of HIVE_PAGE_ZONE_SPECS) {
    test(`${spec.path} renders unified page shell with title "${spec.title}"`, async ({ page }) => {
      test.skip(
        !OPERATOR_CONTROL_PLANE_ENABLED && spec.path === "/agentic-os",
        "Agentic OS shell requires operator control plane",
      );

      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(spec.path, { waitUntil: "domcontentloaded", timeout: 60_000 });

      const shell = page.getByTestId("hive-page-shell");
      await expect(shell).toBeVisible({ timeout: 45_000 });

      const heading = shell.locator("h1");
      await expect(heading).toHaveText(spec.title);

      if (spec.hasSubnav) {
        await expect(shell.locator(".hive-page-shell-subnav")).toBeVisible();
      }
    });
  }

  test("Apps & Tools modules use HivePageShell", async ({ page }) => {
    const modules = [
      "/apps-tools/marketing-automation",
      "/apps-tools/content-factory",
      "/apps-tools/trading-automation",
      "/apps-tools/browser-automation",
      "/apps-tools/research-workspace",
      "/apps-tools/mcp-ops-studio",
    ];

    await page.setViewportSize({ width: 1280, height: 900 });

    for (const path of modules) {
      await page.goto(path, { waitUntil: "domcontentloaded", timeout: 60_000 });
      const shell = page.getByTestId("hive-page-shell");
      await expect(shell).toBeVisible({ timeout: 45_000 });
      await expect(shell.locator("h1")).not.toBeEmpty();
      await expect(shell.locator(".hive-page-shell-subnav")).toBeVisible();
    }
  });

  test("execution lane secondary routes use HivePageShell", async ({ page }) => {
    const routes = [
      { path: "/workflows", title: "Workflows", hasSubnav: true },
      { path: "/jobs", title: "Async workflow jobs" },
      { path: "/foragers", title: "Foragers" },
    ];

    await page.setViewportSize({ width: 1280, height: 900 });

    for (const route of routes) {
      await page.goto(route.path, { waitUntil: "domcontentloaded", timeout: 60_000 });
      const shell = page.getByTestId("hive-page-shell");
      await expect(shell).toBeVisible({ timeout: 45_000 });
      await expect(shell.locator("h1")).toHaveText(route.title);
      if (route.hasSubnav) {
        await expect(shell.locator(".hive-page-shell-subnav")).toBeVisible();
      }
    }
  });

  test("observability secondary routes use HivePageShell", async ({ page }) => {
    const routes = [
      { path: "/monitoring", title: "Monitoring" },
      { path: "/simulations", title: "Simulations" },
    ];

    await page.setViewportSize({ width: 1280, height: 900 });

    for (const route of routes) {
      await page.goto(route.path, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await expect(page).toHaveURL(new RegExp(route.path.replace("/", "\\/")), { timeout: 45_000 });
      const shell = page.getByTestId("hive-page-shell").first();
      await expect(shell).toBeVisible({ timeout: 45_000 });
      await expect(shell.locator("h1")).toHaveText(route.title);
    }
  });
});
