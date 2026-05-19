import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";
import { installShellApiMocks, STUB_AGENT_ID } from "./fixtures/shell-api-mocks";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1280, height: 900 },
] as const;

async function assertNoHorizontalOverflow(page: import("@playwright/test").Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > root.clientWidth + 1;
  });
  expect(overflow, "page should not scroll horizontally").toBe(false);
}

async function gotoShellRoute(page: import("@playwright/test").Page, path: string): Promise<boolean> {
  await page.goto(path, { waitUntil: "load", timeout: 60_000 });
  const currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
  if (currentPath === "/login") {
    return false;
  }
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });
  return true;
}

test.describe("Responsive shell — public login", () => {
  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} login has no horizontal overflow`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/login", { waitUntil: "load", timeout: 45_000 });
      await expect(page.getByRole("button", { name: /continue/i })).toBeVisible({ timeout: 20_000 });
      await assertNoHorizontalOverflow(page);
    });
  }
});

test.describe("Responsive shell — authenticated cockpit", () => {
  test.beforeEach(async ({ page }) => {
    await installShellApiMocks(page);
    await suppressPwaInstallPrompt(page);
  });

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} swarms route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/swarms");
      if (!onShell) {
        expect(new URL(page.url()).searchParams.get("next")).toBe("/swarms");
        return;
      }

      await assertNoHorizontalOverflow(page);

      const desktopRail = page.locator(".hive-sidebar-rail--desktop");
      const bottomNav = page.getByRole("navigation", { name: "Primary mobile navigation" });
      const legacyTopBarSearch = page.locator("#hive-search");

      if (viewport.width < 1024) {
        await expect(desktopRail).toBeHidden();
        await expect(bottomNav).toBeVisible();
      } else {
        await expect(desktopRail).toBeVisible();
        await expect(bottomNav).toBeHidden();
        await expect(legacyTopBarSearch).toHaveCount(0);
      }
    });
  }

  test("desktop dashboard has no duplicate top search bar", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/");
    if (!onShell) {
      return;
    }

    await expect(page.locator("#hive-search")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /queen dashboard/i })).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
  });

  test("tablet integrations hub tab layout", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=hub");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /Dynamic connector hub/i })).toBeVisible({ timeout: 15_000 });
  });

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    test(`${viewport.name} knowledge page layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/knowledge");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible({ timeout: 15_000 });
      await expect(page.locator(".v4-subtab-row").first()).toBeVisible();
    });
  }

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    test(`${viewport.name} agents page layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/agents");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: "Agents", exact: true })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByRole("heading", { name: "Bee role types" })).toBeVisible({ timeout: 15_000 });
    });
  }

  test("mobile drawer covers viewport when open", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/");
    if (!onShell) {
      return;
    }

    await page.getByRole("button", { name: "Open navigation menu" }).click();
    const drawer = page.locator(".hive-sidebar-rail--mobile.hive-sidebar-rail--mobile-open");
    await expect(drawer).toBeVisible({ timeout: 15_000 });

    const drawerWidth = await drawer.evaluate((el) => el.getBoundingClientRect().width);
    const viewportWidth = page.viewportSize()?.width ?? 390;
    expect(drawerWidth).toBeGreaterThanOrEqual(viewportWidth * 0.95);
  });

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} leaderboard route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/leaderboard");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: /leaderboard/i }).first()).toBeVisible({ timeout: 15_000 });
    });
  }

  test("mobile manual page readable layout", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/manual");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Manual" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: /Funkcie aplikácie/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Live dashboard").first()).toBeVisible({ timeout: 15_000 });
  });

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} jobs route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/jobs");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: /async workflow jobs/i })).toBeVisible({ timeout: 15_000 });
    });
  }

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} workflows route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/workflows");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: "Workflows" })).toBeVisible({ timeout: 15_000 });
      await expect(page.locator(".v4-subtab-row").first()).toBeVisible({ timeout: 15_000 });
    });
  }

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} monitoring route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/monitoring");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: "Monitoring" })).toBeVisible({ timeout: 15_000 });
    });
  }

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} simulations route layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/simulations");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: /verified simulation vault/i })).toBeVisible({
        timeout: 15_000,
      });
    });
  }

  test("tablet integrations plugins tab layout", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=plugins");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /Plugins/i })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Drop-in Python plugins/i)).toBeVisible({ timeout: 15_000 });
  });

  test("mobile integrations plugins tab layout", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=plugins");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);
    await expect(page.getByText(/Choose .py file|Drop-in Python plugins/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  const SPRINT8_MOBILE_TABLET_ROUTES = [
    { path: "/costs", heading: "Costs" },
    { path: "/tasks", heading: "Tasks" },
    { path: "/foragers", heading: "Foragers" },
    { path: "/ballroom", heading: "Ballroom" },
    { path: "/settings/security", heading: "Settings" },
  ] as const;

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    for (const route of SPRINT8_MOBILE_TABLET_ROUTES) {
      test(`${viewport.name} ${route.path} layout`, async ({ page, context, baseURL }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

        const onShell = await gotoShellRoute(page, route.path);
        if (!onShell) {
          return;
        }

        await assertNoHorizontalOverflow(page);
        await expect(page.getByRole("heading", { name: route.heading, exact: true }).first()).toBeVisible({
          timeout: 15_000,
        });
      });
    }
  }

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    test(`${viewport.name} dashboard queen layout`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: /queen dashboard/i })).toBeVisible({ timeout: 15_000 });
      await expect(page.locator("#hive-search")).toHaveCount(0);
    });
  }

  const SPRINT9_MOBILE_TABLET_ROUTES = [
    { path: `/agents/${STUB_AGENT_ID}`, heading: "Scout Bee" },
    { path: "/agents/new", heading: "Spawn agent" },
    { path: "/tasks/new", heading: "New task" },
    { path: "/settings/billing", heading: "Usage & Billing" },
    { path: "/settings/team", heading: "Team & RBAC" },
    { path: "/settings/audit", heading: "Audit log" },
    { path: "/settings/api-keys", heading: "External data APIs" },
  ] as const;

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    for (const route of SPRINT9_MOBILE_TABLET_ROUTES) {
      test(`${viewport.name} ${route.path} layout`, async ({ page, context, baseURL }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

        const onShell = await gotoShellRoute(page, route.path);
        if (!onShell) {
          return;
        }

        await assertNoHorizontalOverflow(page);
        await expect(page.getByRole("heading", { name: route.heading, exact: true }).first()).toBeVisible({
          timeout: 15_000,
        });
      });
    }
  }

  const SPRINT10_MOBILE_TABLET_ROUTES = [
    { path: `/agents/${STUB_AGENT_ID}/edit`, heading: /Scout Bee/ },
    { path: "/settings/llm-keys", heading: "Grok (xAI)" },
    { path: "/settings/notifications", heading: "Email" },
    { path: "/settings/sharing", heading: "Public sharing" },
  ] as const;

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    for (const route of SPRINT10_MOBILE_TABLET_ROUTES) {
      test(`${viewport.name} ${route.path} layout`, async ({ page, context, baseURL }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

        const onShell = await gotoShellRoute(page, route.path);
        if (!onShell) {
          return;
        }

        await assertNoHorizontalOverflow(page);
        await expect(page.getByRole("heading", { name: route.heading }).first()).toBeVisible({
          timeout: 15_000,
        });
      });
    }
  }
});
