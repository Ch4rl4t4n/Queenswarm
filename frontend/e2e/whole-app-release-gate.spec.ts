import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { HIVE_RELEASE_GATE_INVARIANTS } from "../lib/hive-release-gate-spec";
import { hiveModalMigrationComplete } from "../lib/hive-modal-migration-spec";
import { hivePopoverMigrationCompleteForPhase123 } from "../lib/hive-popover-spec";
import { HIVE_PAGE_ZONE_SPECS } from "../lib/hive-page-zone-spec";
import { DESKTOP_MIN_PX } from "../lib/breakpoints";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

async function gotoShellRoute(page: import("@playwright/test").Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });
}

test.describe("Whole-App release gate — structural invariants", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.setViewportSize({ width: DESKTOP_MIN_PX, height: 900 });
  });

  test(`invariant registry documents ${HIVE_RELEASE_GATE_INVARIANTS.length} checks`, () => {
    expect(HIVE_RELEASE_GATE_INVARIANTS.map((row) => row.id)).toContain("desktop-no-duplicate-search");
    expect(HIVE_RELEASE_GATE_INVARIANTS.map((row) => row.id)).toContain("modal-migration-complete");
    expect(HIVE_RELEASE_GATE_INVARIANTS.map((row) => row.id)).toContain("popover-migration-complete");
  });

  test("invariant: modal migration complete (HiveModalShell SSOT)", () => {
    expect(hiveModalMigrationComplete()).toBe(true);
  });

  test("invariant: popover migration complete (HivePopoverShell SSOT)", () => {
    expect(hivePopoverMigrationCompleteForPhase123()).toBe(true);
  });

  for (const spec of HIVE_PAGE_ZONE_SPECS) {
    test(`desktop ${spec.path} — shell, title, no duplicate search`, async ({ page }) => {
      test.skip(
        !OPERATOR_CONTROL_PLANE_ENABLED && spec.path === "/agentic-os",
        "Agentic OS requires operator control plane",
      );

      await gotoShellRoute(page, spec.path);

      await expect(page.locator("#hive-search")).toHaveCount(0);
      await expect(page.locator(".hive-sidebar-rail--desktop")).toBeVisible();
      await expect(page.getByTestId("hive-mobile-header")).toBeHidden();
      await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeHidden();

      const shell = page.getByTestId("hive-page-shell");
      await expect(shell).toBeVisible({ timeout: 45_000 });
      await expect(shell.locator("h1")).toHaveText(spec.title);
    });
  }

  test("invariant: no legacy Cockpit h1 on Agentic OS route", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await gotoShellRoute(page, "/agentic-os");
    await expect(page.getByTestId("hive-page-shell").locator("h1")).toHaveText("Agentic OS");
    await expect(page.getByRole("heading", { name: /^Cockpit$/i })).toHaveCount(0);
  });

  test("invariant: settings shell uses progressive subnav", async ({ page }) => {
    await gotoShellRoute(page, "/settings/security");
    await expect(page.getByTestId("hive-page-shell")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Settings groups" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("navigation", { name: "Settings sections" })).toBeVisible();
  });

  test("invariant: Apps & Tools index exposes module grid", async ({ page }) => {
    await gotoShellRoute(page, "/apps-tools");
    await expect(page.getByRole("heading", { name: "Module index" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Skill Factory", { exact: true })).toBeVisible({ timeout: 30_000 });
  });
});
