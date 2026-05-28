import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { MOBILE_TABLET_SECONDARY_ROUTE_SPECS, MOBILE_TABLET_ZONE_ROUTE_SPECS } from "../lib/mobile-tablet-zone-spec";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";
import { DESKTOP_MIN_PX, MOBILE_MAX_PX, TABLET_MIN_PX } from "../lib/breakpoints";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: TABLET_MIN_PX, height: 1024 },
] as const;

async function assertNoHorizontalOverflow(page: import("@playwright/test").Page): Promise<void> {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  expect(overflow, "page should not scroll horizontally").toBe(false);
}

async function assertRouteLoaded(
  page: import("@playwright/test").Page,
  spec: (typeof MOBILE_TABLET_ZONE_ROUTE_SPECS)[number] | (typeof MOBILE_TABLET_SECONDARY_ROUTE_SPECS)[number],
): Promise<void> {
  if (spec.shellTitle) {
    const shell = page.getByTestId("hive-page-shell");
    if ((await shell.count()) > 0) {
      await expect(shell.locator("h1")).toHaveText(spec.shellTitle);
      if (spec.panelHeading) {
        await expect(page.getByRole("heading", { name: spec.panelHeading }).first()).toBeVisible({
          timeout: 15_000,
        });
      }
      return;
    }
  }
  if (spec.contentHeading) {
    await expect(page.getByRole("heading", { name: spec.contentHeading }).first()).toBeVisible({
      timeout: 15_000,
    });
  }
}

test.describe("Whole-App mobile/tablet — zone chrome", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("desktop hides mobile header and bottom nav", async ({ page }) => {
    await page.setViewportSize({ width: DESKTOP_MIN_PX, height: 900 });
    await page.goto("/swarms", { waitUntil: "domcontentloaded", timeout: 60_000 });

    await expect(page.getByTestId("hive-mobile-header")).toBeHidden({ timeout: 45_000 });
    await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeHidden();
    await expect(page.locator(".hive-sidebar-rail--desktop")).toBeVisible();
  });

  for (const viewport of VIEWPORTS) {
    for (const spec of MOBILE_TABLET_ZONE_ROUTE_SPECS) {
      test(`${viewport.name} ${spec.path} — shell, title, no overflow`, async ({ page }) => {
        test.skip(
          Boolean(spec.requiresCp) && !OPERATOR_CONTROL_PLANE_ENABLED,
          "Agentic OS routes require operator control plane",
        );

        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto(spec.path, { waitUntil: "domcontentloaded", timeout: 60_000 });

        await expect(page.getByTestId("hive-mobile-header")).toBeVisible({ timeout: 45_000 });
        await expect(page.getByTestId("hive-mobile-header-title")).toContainText(spec.mobileTitle);

        const bottomNav = page.getByRole("navigation", { name: "Primary mobile navigation" });
        await expect(bottomNav).toBeVisible();

        if (spec.shellTitle) {
          await assertRouteLoaded(page, spec);
        } else if (spec.contentHeading) {
          await assertRouteLoaded(page, spec);
        }

        await assertNoHorizontalOverflow(page);
      });
    }
  }

  for (const viewport of VIEWPORTS) {
    for (const spec of MOBILE_TABLET_SECONDARY_ROUTE_SPECS) {
      test(`${viewport.name} secondary ${spec.path} — title, no overflow`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto(spec.path, { waitUntil: "domcontentloaded", timeout: 60_000 });

        await expect(page.getByTestId("hive-mobile-header")).toBeVisible({ timeout: 45_000 });
        await expect(page.getByTestId("hive-mobile-header-title")).toContainText(spec.mobileTitle);
        await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeVisible();

        await assertRouteLoaded(page, spec);
        await assertNoHorizontalOverflow(page);
      });
    }
  }

  test("mobile viewport width stays within phone tier", () => {
    expect(MOBILE_MAX_PX).toBeLessThan(DESKTOP_MIN_PX);
    expect(TABLET_MIN_PX).toBeLessThan(DESKTOP_MIN_PX);
  });
});
