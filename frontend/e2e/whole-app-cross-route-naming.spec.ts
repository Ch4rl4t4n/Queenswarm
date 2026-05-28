import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

test.describe("Whole-App cross-route naming", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("page shell shows Agentic OS on canonical route (mobile + desktop)", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "CP naming applies only when operator control plane is enabled");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/agentic-os", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const shell = page.getByTestId("hive-page-shell");
    await expect(shell).toBeVisible({ timeout: 45_000 });
    await expect(shell.locator("h1")).toHaveText("Agentic OS");
  });

  test("sidebar primary item reads Agentic OS not Cockpit", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "CP naming applies only when operator control plane is enabled");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/swarms", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const nav = page.locator('nav[aria-label="Hive navigation"]');
    await expect(nav.getByText("Agentic OS", { exact: true })).toBeVisible({ timeout: 45_000 });
    await expect(nav.getByText("Cockpit", { exact: true })).toHaveCount(0);
  });
});
