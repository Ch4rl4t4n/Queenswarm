import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import {
  e2eHiveHomeHeading,
  e2eHiveHomePath,
  e2eTasksHubHeading,
  e2eTasksSidebarLabel,
} from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { HIVE_CRITICAL_JOURNEY_SPECS } from "../lib/hive-critical-journeys-spec";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

const SIDEBAR_ROUTE_PATTERN: Record<string, RegExp> = {
  Swarms: /\/swarms(?:\?|#|$)/,
  Tasks: /\/tasks(?:\?|#|$)/,
  "Mission Control": /\/tasks(?:\?|#|$)/,
  Agents: /\/agents(?:\?|#|$)/,
  "Apps & Tools": /\/apps-tools(?:\?|#|$)/,
  Integrations: /\/integrations(?:\?|#|$)/,
  Knowledge: /\/knowledge(?:\?|#|$)/,
};

async function gotoShellRoute(
  page: import("@playwright/test").Page,
  path: string,
  options?: { waitForMobileNav?: boolean },
): Promise<void> {
  const pathname = path.split("?")[0]?.split("#")[0] ?? path;
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await expect(page).toHaveURL(new RegExp(`${pathname.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?:[?#]|$)`), {
    timeout: 45_000,
  });
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });
  if (options?.waitForMobileNav) {
    await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeVisible({
      timeout: 20_000,
    });
  }
}

async function assertShellTitle(
  page: import("@playwright/test").Page,
  title: string | RegExp,
  urlPattern?: RegExp,
): Promise<void> {
  if (urlPattern) {
    await expect(page).toHaveURL(urlPattern, { timeout: 45_000 });
  }
  const shell = page.getByTestId("hive-page-shell");
  await expect(shell).toBeVisible({ timeout: 45_000 });
  await expect(shell.locator("h1")).toHaveText(title);
}

async function clickSidebarNav(page: import("@playwright/test").Page, label: string): Promise<void> {
  const nav = page.locator(".hive-sidebar-rail--desktop nav[aria-label='Hive navigation']");
  await expect(nav).toBeVisible({ timeout: 20_000 });
  const link = nav.getByRole("link", { name: new RegExp(`^${label}\\b`) });
  const routePattern = SIDEBAR_ROUTE_PATTERN[label];
  if (routePattern) {
    await Promise.all([
      page.waitForURL(routePattern, { timeout: 45_000, waitUntil: "domcontentloaded" }),
      link.click(),
    ]);
    return;
  }
  await link.click();
}

async function clickSubnavTab(
  page: import("@playwright/test").Page,
  navLabel: string,
  tabLabel: string,
): Promise<void> {
  const nav = page.getByRole("navigation", { name: navLabel });
  await expect(nav).toBeVisible({ timeout: 20_000 });
  const tabPattern = new RegExp(`^${tabLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\b|$)`, "i");
  const tabButton = nav.getByRole("button", { name: tabPattern });
  if ((await tabButton.count()) > 0) {
    await tabButton.first().click();
    return;
  }
  await nav.getByRole("link", { name: tabPattern }).first().click();
}

function journeySpec(id: string) {
  return HIVE_CRITICAL_JOURNEY_SPECS.find((row) => row.id === id);
}

test.describe("Whole-App critical journeys — desktop", () => {
  test.describe.configure({ mode: "serial", timeout: 90_000 });

  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test(`${journeySpec("operator-bootstrap")?.id}: home shell without duplicate search`, async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, journeySpec("operator-bootstrap")?.description);

    await gotoShellRoute(page, e2eHiveHomePath());
    await expect(page.locator("#hive-search")).toHaveCount(0);
    await assertShellTitle(page, e2eHiveHomeHeading());
  });

  test(`${journeySpec("agentic-os-sidebar-loop")?.id}: sidebar zone loop`, async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, journeySpec("agentic-os-sidebar-loop")?.description);

    await gotoShellRoute(page, "/agentic-os");
    await assertShellTitle(page, "Agentic OS");

    const tasksNav = e2eTasksSidebarLabel();
    for (const label of ["Swarms", tasksNav, "Agents"] as const) {
      await clickSidebarNav(page, label);
      await assertShellTitle(page, label === tasksNav ? e2eTasksHubHeading() : label);
    }
  });

  test(`${journeySpec("agentic-os-subnav-command")?.id}: command lane subnav`, async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, journeySpec("agentic-os-subnav-command")?.description);

    await gotoShellRoute(page, "/agentic-os");
    await expect(page.getByRole("navigation", { name: "Agentic OS sections" })).toBeVisible({
      timeout: 20_000,
    });

    const expandAdvanced = page.getByRole("button", { name: /Show advanced tools/i });
    try {
      await expandAdvanced.click({ timeout: 8_000 });
      await clickSubnavTab(page, "Advanced Agentic OS tools", "Command");
    } catch {
      await clickSubnavTab(page, "Agentic OS sections", "Command");
    }
    await expect(page.getByText("Bee Hotline")).toBeVisible({ timeout: 20_000 });
  });

  test(`${journeySpec("apps-tools-discovery")?.id}: module index to Skill Factory`, async ({ page }) => {
    await gotoShellRoute(page, "/apps-tools");
    await assertShellTitle(page, "Apps & Tools", /\/apps-tools(?:\/|$|\?|#)/);

    await expect(page.getByRole("heading", { name: "Module index" })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('a[href="/apps-tools/skill-factory"]').filter({ hasText: /^Configure$/ })).toBeVisible({
      timeout: 30_000,
    });

    await gotoShellRoute(page, "/apps-tools/skill-factory");
    await assertShellTitle(page, "Apps & Tools", /\/apps-tools\/skill-factory(?:[?#]|$)/);
  });

  test(`${journeySpec("integrations-tab-switch")?.id}: skills export tab`, async ({ page }) => {
    await gotoShellRoute(page, "/integrations");
    await assertShellTitle(page, "Integrations");

    const sections = page.getByRole("navigation", { name: "Integration sections" });
    await expect(sections).toBeVisible({ timeout: 20_000 });
    const skillsTab = sections.getByRole("button", { name: /Skills export/i });
    await expect(skillsTab).toBeVisible({ timeout: 15_000 });
    await skillsTab.click();
    await expect(page).toHaveURL(/tab=skills/, { timeout: 15_000 });
  });

  test(`${journeySpec("knowledge-subnav")?.id}: recipes section`, async ({ page }) => {
    await gotoShellRoute(page, "/knowledge");
    await assertShellTitle(page, "Knowledge");

    await clickSubnavTab(page, "Knowledge sections", "Recipes · Learning");
    await expect(page).toHaveURL(/#recipes/, { timeout: 15_000 });
  });

  test(`${journeySpec("settings-progressive")?.id}: advanced disclosure to api keys`, async ({ page }) => {
    await gotoShellRoute(page, "/settings/security");
    await assertShellTitle(page, "Settings");

    const expand = page.getByRole("button", { name: "Show advanced settings" });
    if (await expand.isVisible()) {
      await expand.click();
    }

    await clickSubnavTab(page, "Settings groups", "Advanced");
    await clickSubnavTab(page, "Settings sections", "API keys");

    await expect(page).toHaveURL(/\/settings\/api-keys/, { timeout: 15_000 });
    await expect(page.getByText(/External data APIs/i).first()).toBeVisible({ timeout: 20_000 });
  });

  test(`${journeySpec("execution-new-task")?.id}: tasks queue to new task wizard`, async ({ page }) => {
    await gotoShellRoute(page, "/tasks");
    await assertShellTitle(page, e2eTasksHubHeading());

    const newTask = page.getByRole("link", { name: "New task" }).first();
    await expect(newTask).toBeVisible({ timeout: 20_000 });
    await newTask.click();
    await expect(page).toHaveURL(/\/tasks\/new/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "New task" })).toBeVisible({ timeout: 20_000 });
  });

  test(`${journeySpec("legacy-cockpit-redirect")?.id}: legacy hash preserved`, async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, journeySpec("legacy-cockpit-redirect")?.description);

    await page.goto("/cockpit#icm", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page).toHaveURL(/\/agentic-os#icm/, { timeout: 45_000 });
    await assertShellTitle(page, "Agentic OS");
  });
});

test.describe("Whole-App critical journeys — mobile", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.setViewportSize({ width: 390, height: 844 });
  });

  test(`${journeySpec("mobile-more-foragers")?.id ?? "mobile-more-foragers"}: overflow menu reaches foragers`, async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, journeySpec("mobile-more-foragers")?.description ?? "Mobile overflow → Foragers");

    await gotoShellRoute(page, "/swarms", { waitForMobileNav: true });

    const more = page.getByRole("button", { name: "More" });
    await expect(more).toBeVisible({ timeout: 15_000 });
    await more.click();

    const sheet = page.getByRole("dialog", { name: /Hive navigation/i });
    await expect(sheet).toBeVisible({ timeout: 15_000 });
    await sheet.getByRole("link", { name: "Foragers" }).click();
    await expect(page).toHaveURL(/\/foragers/, { timeout: 45_000 });

    await assertShellTitle(page, "Foragers");
    await expect(page.getByTestId("hive-mobile-header-title")).toContainText("QueenSwarm");
  });
});
