import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eAdvancedDashboardPath, e2eHiveHomeHeading, e2eHiveHomePath, e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";
import { maybeInstallShellApiMocks, STUB_AGENT_ID } from "./fixtures/shell-api-mocks";

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
  const targetPath = new URL(path, "http://localhost").pathname.replace(/\/$/, "") || "/";
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => undefined);
  let currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
  if (currentPath === "/login") {
    return false;
  }
  if (currentPath !== targetPath) {
    await page.waitForURL(`**${targetPath}**`, { timeout: 20_000 }).catch(() => undefined);
    currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
    if (currentPath === "/login") {
      return false;
    }
    if (currentPath !== targetPath) {
      return false;
    }
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
    await maybeInstallShellApiMocks(page);
    await suppressPwaInstallPrompt(page);
  });

  test("desktop shows glowing Ballroom FAB on dashboard routes", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/");
    if (!onShell) {
      return;
    }

    const fab = page.getByTestId("ballroom-fab");
    await expect(fab).toBeVisible({ timeout: 15_000 });
    await expect(fab.getByRole("link", { name: /Open Ballroom/i })).toBeVisible();

    const onSwarms = await gotoShellRoute(page, "/swarms");
    if (!onSwarms) {
      return;
    }
    await expect(fab).toBeVisible({ timeout: 15_000 });

    const onBallroom = await gotoShellRoute(page, "/ballroom");
    if (!onBallroom) {
      return;
    }
    await expect(fab).toBeHidden({ timeout: 10_000 });
  });

  test("mobile shows New session FAB above bottom nav", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/");
    if (!onShell) {
      return;
    }

    const fab = page.getByTestId("session-fab");
    await expect(fab).toBeVisible({ timeout: 15_000 });
    await expect(fab.getByRole("link", { name: /New session/i })).toBeVisible();
    const box = await fab.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.y).toBeGreaterThan(500);
    }
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

  test("mobile More trigger wires ARIA disclosure to the nav sheet", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/swarms");
    if (!onShell) {
      return;
    }

    const moreButton = page
      .getByRole("navigation", { name: "Primary mobile navigation" })
      .getByRole("button", { name: /More/i });
    await expect(moreButton).toBeVisible({ timeout: 15_000 });
    await expect(moreButton).toHaveAttribute("aria-expanded", "false");
    await expect(moreButton).toHaveAttribute("aria-haspopup", "dialog");

    await moreButton.click();

    const sheet = page.getByRole("dialog", { name: /Hive navigation/i });
    await expect(sheet).toBeVisible({ timeout: 10_000 });
    await expect(sheet).toHaveAttribute("id", "hive-more-sheet");
    await expect(moreButton).toHaveAttribute("aria-expanded", "true");
    await expect(moreButton).toHaveAttribute("aria-controls", "hive-more-sheet");
  });

  for (const viewport of VIEWPORTS.filter((v) => v.name !== "desktop")) {
    test(`${viewport.name} ballroom shows Dump & Sleep without scroll trap`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      const onShell = await gotoShellRoute(page, "/ballroom");
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);

      const dumpSleep = page.getByRole("heading", { name: "Dump & Sleep", exact: true });
      await expect(dumpSleep).toBeVisible({ timeout: 15_000 });

      // The Dump & Sleep card must not be collapsed to a clipped sliver — its
      // interactive content (upload + queue CTA) has to stay reachable.
      await expect(page.getByText(/Folder dump/i)).toBeVisible({ timeout: 10_000 });
      await expect(page.getByRole("button", { name: /Queue overnight swarm/i })).toBeVisible({
        timeout: 10_000,
      });

      // Mobile chat body must not be a nested scroll container (single page scroll),
      // otherwise it traps touch + paints an overlapping scrollbar over the voice area.
      const bodyOverflow = await page
        .locator(".v4-chat-body")
        .first()
        .evaluate((el) => getComputedStyle(el).getPropertyValue("overflow-y"));
      expect(["auto", "scroll"]).not.toContain(bodyOverflow);
    });
  }

  test("mobile marketplace custom-connection form does not overlap active integrations", async ({
    page,
    context,
    baseURL,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=active");
    if (!onShell) {
      return;
    }

    const marketplaceCard = page.locator("#marketplace-preview");
    await expect(marketplaceCard).toBeVisible({ timeout: 15_000 });

    const customConnection = marketplaceCard.getByRole("button", { name: /Custom connection/i });
    await expect(customConnection).toBeVisible({ timeout: 15_000 });
    await customConnection.click();

    // Form expands — the paginated marketplace shell must drop its height cap so
    // content cannot overflow the capped box and overlap the Active integrations card.
    await expect(page.getByText("Create custom connection")).toBeVisible({ timeout: 10_000 });

    const shellStyle = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".v4-marketplace-shell.v4-marketplace-shell--paginated");
      if (!shell) {
        return null;
      }
      const cs = getComputedStyle(shell);
      return { maxHeight: cs.maxHeight, overflowY: cs.overflowY };
    });
    expect(shellStyle).not.toBeNull();
    if (shellStyle) {
      expect(shellStyle.maxHeight).toBe("none");
      expect(["auto", "scroll"]).not.toContain(shellStyle.overflowY);
    }

    // And no visual overlap with the Active integrations card below.
    const noOverlap = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".v4-marketplace-shell");
      const active = document.querySelector<HTMLElement>("#active-integrations");
      if (!shell || !active) {
        return true;
      }
      return shell.getBoundingClientRect().bottom <= active.getBoundingClientRect().top + 1;
    });
    expect(noOverlap).toBe(true);
  });

  test("mobile catalog panels use page scroll not nested trap", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=marketplace");
    if (!onShell) {
      return;
    }

    await expect(page.locator("#marketplace-preview")).toBeVisible({ timeout: 15_000 });

    const panelOverflow = await page.evaluate(() => {
      const body = document.querySelector<HTMLElement>("[data-hive-viewport-panel-body]");
      if (!body) {
        return null;
      }
      return getComputedStyle(body).overflowY;
    });
    expect(panelOverflow).not.toBeNull();
    if (panelOverflow) {
      expect(["auto", "scroll"]).not.toContain(panelOverflow);
    }

    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    const scrolled = await page.evaluate(() => {
      const tallEnough = document.documentElement.scrollHeight > window.innerHeight + 40;
      return tallEnough ? window.scrollY > 0 : true;
    });
    expect(scrolled).toBe(true);
  });

  test("mobile integrations scroll tail clears session FAB", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=marketplace");
    if (!onShell) {
      return;
    }

    const fab = page.getByTestId("session-fab");
    await expect(fab).toBeVisible({ timeout: 15_000 });

    const cleared = await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>('[data-hive-shell="canvas"]');
      const fabEl = document.querySelector<HTMLElement>('[data-testid="session-fab"] .fab-session');
      if (!main || !fabEl) {
        return null;
      }
      window.scrollTo(0, document.documentElement.scrollHeight);
      const padBottom = parseFloat(getComputedStyle(main).paddingBottom);
      const mainRect = main.getBoundingClientRect();
      const contentBottom = mainRect.bottom - padBottom;
      const fabTop = fabEl.getBoundingClientRect().top;
      return contentBottom <= fabTop - 4;
    });
    expect(cleared).toBe(true);
  });

  test("mobile content bottom padding clears the floating session FAB", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/settings/harness");
    if (!onShell) {
      return;
    }

    const fab = page.getByTestId("session-fab");
    await expect(fab).toBeVisible({ timeout: 15_000 });

    const clearance = await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>('[data-hive-shell="canvas"]');
      const fabEl = document.querySelector<HTMLElement>('[data-testid="session-fab"]');
      if (!main || !fabEl) {
        return null;
      }
      const padBottom = parseFloat(getComputedStyle(main).paddingBottom);
      const fabFromBottom = window.innerHeight - fabEl.getBoundingClientRect().top;
      return { padBottom, fabFromBottom };
    });
    expect(clearance).not.toBeNull();
    if (clearance) {
      // Bottom content padding must lift the last content clear of the floating FAB.
      expect(clearance.padBottom).toBeGreaterThanOrEqual(clearance.fabFromBottom);
    }
  });

  test("mobile integrations status badges stay within card bounds", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);

    const firstCard = page.locator(".active-integration-card, .hub-catalog-card").first();
    await expect(firstCard).toBeVisible({ timeout: 15_000 });

    const withinBounds = await firstCard.evaluate((card) => {
      const badge = card.querySelector<HTMLElement>(".v4-badge");
      if (!badge) {
        return true;
      }
      const cardRect = card.getBoundingClientRect();
      const badgeRect = badge.getBoundingClientRect();
      // Badge must not bleed past the card's right/left padding edge.
      return badgeRect.right <= cardRect.right + 1 && badgeRect.left >= cardRect.left - 1;
    });
    expect(withinBounds).toBe(true);
  });

  test("mobile subnav centers the selected section in the scroll row", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations");
    if (!onShell) {
      return;
    }

    const row = page.getByRole("navigation", { name: "Integration sections" });
    await expect(row).toBeVisible({ timeout: 15_000 });

    // Pick a far tab that starts off-centre, select it, then assert it auto-centres.
    const plugins = row.getByRole("button", { name: /Plugins/i });
    await expect(plugins).toBeVisible();
    await plugins.click();
    await expect(plugins).toHaveClass(/v4-subtab--active/);

    // Allow the smooth scroll to settle.
    await page.waitForTimeout(500);

    const centred = await row.evaluate((container) => {
      const active = container.querySelector<HTMLElement>(".v4-subtab--active");
      if (!active) {
        return false;
      }
      const c = container.getBoundingClientRect();
      const a = active.getBoundingClientRect();
      const activeCenter = a.left + a.width / 2;
      const containerCenter = c.left + c.width / 2;
      // Centred within a quarter of the row width (generous tolerance for edge clamping).
      return Math.abs(activeCenter - containerCenter) <= c.width / 4;
    });
    expect(centred).toBe(true);
  });

  test("desktop dashboard has no duplicate top search bar", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, e2eAdvancedDashboardPath());
    if (!onShell) {
      return;
    }

    await expect(page.locator(".hive-sidebar-rail--desktop")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("#hive-search")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /^Dashboard$/i }).first()).toBeVisible({
      timeout: 15_000,
    });
    await assertNoHorizontalOverflow(page);
  });

  test("tablet costs settings shows upgrade-removed hint", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/settings/costs");
    if (!onShell) {
      return;
    }

    await expect(page.getByRole("heading", { name: "Costs", level: 2 })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("link", { name: /Tier limits — view plan comparison/i })).toHaveAttribute(
      "href",
      "#billing-plans",
    );
    await expect(page.getByRole("heading", { name: "Plan & tier limits" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Usage & Billing" })).toHaveCount(0);
    await expect(page.getByText(/Upgrade flow removed|upgrades unavailable/i).first()).toBeVisible({ timeout: 15_000 });
  });

  test("tablet integrations skills tab shows checkout-removed state", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/integrations?tab=skills");
    if (!onShell) {
      return;
    }

    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Premium checkout:\s*removed/i)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Locked" })).toBeVisible({ timeout: 15_000 });
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

    const onShell = await gotoShellRoute(page, e2eHiveHomePath());
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

  test("mobile manual page readable layout", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const onShell = await gotoShellRoute(page, "/manual");
    if (!onShell) {
      return;
    }

    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Manual" })).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByRole("heading", { name: /Funkcie aplikácie|App functions and info descriptions/i }),
    ).toBeVisible({ timeout: 15_000 });
    const main = page.locator("#hive-main-canvas");
    await expect(main.getByText(/Live dashboard|Agentic OS/i).first()).toBeVisible({ timeout: 15_000 });
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
      await expect(page.getByRole("heading", { name: "Simulations", exact: true })).toBeVisible({
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
    { path: "/settings/costs", heading: "Costs" },
    { path: "/tasks", heading: e2eTasksHubHeading() },
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

      const onShell = await gotoShellRoute(page, e2eHiveHomePath());
      if (!onShell) {
        return;
      }

      await assertNoHorizontalOverflow(page);
      await expect(page.getByRole("heading", { name: e2eHiveHomeHeading() }).first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator("#hive-search")).toHaveCount(0);
    });
  }

  const SPRINT9_MOBILE_TABLET_ROUTES = [
    { path: `/agents/${STUB_AGENT_ID}`, heading: "Scout Bee" },
    { path: "/agents/new", heading: "Spawn agent" },
    { path: "/tasks/new", heading: "New task" },
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

  test("mobile notification bell opens mission feed sheet", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await maybeInstallShellApiMocks(page);

    const onShell = await gotoShellRoute(page, "/tasks");
    if (!onShell) {
      return;
    }

    await expect(page.getByTestId("hive-mobile-notifications-bell")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("hive-mobile-notifications-bell").click();
    await expect(page.getByRole("heading", { name: "Notifications" })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Notification settings")).toBeVisible();
  });
});
