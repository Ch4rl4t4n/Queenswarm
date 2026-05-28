import { expect, test } from "@playwright/test";

import { seedDashboardAccessToken } from "./fixtures/dashboard-session";
import { e2eHiveHomePath } from "./fixtures/hive-home-route";
import {
  HIVE_PROD_JOURNEY_ROUTES,
  HIVE_PROD_JOURNEY_ZONE_ROUTES,
} from "../lib/hive-prod-journey-spec";
import { DESKTOP_MIN_PX } from "../lib/breakpoints";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

const enabled = process.env.E2E_PROD_AUTHENTICATED === "1";
const accessToken = process.env.OPERATOR_USER_BEARER_TOKEN?.trim() ?? "";

async function gotoAuthenticatedRoute(page: import("@playwright/test").Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 90_000 });
  const currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
  expect(currentPath, `expected ${path}, got ${currentPath} (login redirect?)`).not.toBe("/login");
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 60_000 });
}

test.describe("Whole-App prod journeys — authenticated matrix", () => {
  test.skip(!enabled || !accessToken, "Set E2E_PROD_AUTHENTICATED=1 and OPERATOR_USER_BEARER_TOKEN.");

  test.beforeEach(async ({ page, context, baseURL }) => {
    await seedDashboardAccessToken(context, baseURL ?? "https://queenswarm.love", accessToken);
    await page.setViewportSize({ width: DESKTOP_MIN_PX, height: 900 });
  });

  test("operator bootstrap — home shell without duplicate search", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane on target hive");

    await gotoAuthenticatedRoute(page, e2eHiveHomePath());
    await expect(page.locator("#hive-search")).toHaveCount(0);
    await expect(page.getByTestId("hive-page-shell")).toBeVisible({ timeout: 45_000 });
  });

  for (const spec of HIVE_PROD_JOURNEY_ZONE_ROUTES) {
    test(`zone ${spec.path} loads shell`, async ({ page }) => {
      test.skip(Boolean(spec.requiresCp) && !OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

      await gotoAuthenticatedRoute(page, spec.path);

      if (spec.shellTitle) {
        const shell = page.getByTestId("hive-page-shell");
        if ((await shell.count()) > 0) {
          await expect(shell.locator("h1")).toHaveText(spec.shellTitle, { timeout: 45_000 });
          return;
        }
      }
      if (spec.shellTitle) {
        await expect(page.getByRole("heading", { name: spec.shellTitle, exact: true }).first()).toBeVisible({
          timeout: 45_000,
        });
      }
    });
  }

  const zonePaths = new Set(HIVE_PROD_JOURNEY_ZONE_ROUTES.map((row) => row.path));
  const secondaryRoutes = HIVE_PROD_JOURNEY_ROUTES.filter((row) => !zonePaths.has(row.path));

  for (const spec of secondaryRoutes) {
    test(`secondary ${spec.path} loads`, async ({ page }) => {
      await gotoAuthenticatedRoute(page, spec.path);

      if (spec.shellTitle) {
        const shell = page.getByTestId("hive-page-shell");
        if ((await shell.count()) > 0) {
          await expect(shell.locator("h1")).toHaveText(spec.shellTitle, { timeout: 45_000 });
          return;
        }
      }
      if (spec.heading) {
        await expect(page.getByRole("heading", { name: spec.heading, exact: true }).first()).toBeVisible({
          timeout: 45_000,
        });
      }
    });
  }

  test("legacy /cockpit redirects to agentic-os", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.goto("/cockpit", { waitUntil: "domcontentloaded", timeout: 90_000 });
    await expect(page).toHaveURL(/\/agentic-os/, { timeout: 45_000 });
  });
});
