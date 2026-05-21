import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";
import { installShellApiMocks, STUB_AGENT_ID } from "./fixtures/shell-api-mocks";
import { stabilizePageForScreenshot } from "./fixtures/visual-stable";

/** Mobile + tablet only — desktop layout must never be snapshotted here. */
const MOBILE_TABLET_VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
] as const;

interface SnapshotRoute {
  path: string;
  slug: string;
  public?: boolean;
  heading?: string | RegExp;
  headingExact?: boolean;
}

const SNAPSHOT_ROUTES: SnapshotRoute[] = [
  { path: "/login", slug: "login", public: true },
  { path: "/", slug: "dashboard", heading: /^Dashboard$/i },
  { path: "/swarms", slug: "swarms", heading: /swarms/i },
  { path: "/tasks", slug: "tasks", heading: "Tasks", headingExact: true },
  { path: "/agents", slug: "agents", heading: "Agents", headingExact: true },
  { path: "/knowledge", slug: "knowledge", heading: "Knowledge" },
  { path: "/costs", slug: "costs", heading: "Costs", headingExact: true },
  { path: "/settings/security", slug: "settings-security", heading: "Settings", headingExact: true },
  { path: "/foragers", slug: "foragers", heading: "Foragers", headingExact: true },
  { path: "/ballroom", slug: "ballroom", heading: "Ballroom", headingExact: true },
  { path: "/integrations?tab=hub", slug: "integrations-hub", heading: "Integrations", headingExact: true },
  { path: `/agents/${STUB_AGENT_ID}`, slug: "agent-detail", heading: "Scout Bee", headingExact: true },
  { path: "/monitoring", slug: "monitoring", heading: "Monitoring", headingExact: true },
  { path: "/workflows", slug: "workflows", heading: "Workflows", headingExact: true },
];

async function gotoReadyShell(
  page: import("@playwright/test").Page,
  route: SnapshotRoute,
): Promise<boolean> {
  await page.goto(route.path, { waitUntil: "load", timeout: 60_000 });

  const currentPath = new URL(page.url()).pathname.replace(/\/$/, "") || "/";
  if (currentPath === "/login" && route.path !== "/login") {
    return false;
  }

  if (route.public) {
    await expect(page.getByRole("button", { name: /continue/i })).toBeVisible({ timeout: 20_000 });
    return true;
  }

  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });

  if (route.heading) {
    await expect(
      page.getByRole("heading", { name: route.heading, exact: route.headingExact ?? false }),
    ).toBeVisible({ timeout: 20_000 });
  }

  return true;
}

test.describe("Responsive visual — mobile + tablet snapshots", () => {
  test.beforeEach(async ({ page }) => {
    await installShellApiMocks(page);
    await suppressPwaInstallPrompt(page);
  });

  for (const viewport of MOBILE_TABLET_VIEWPORTS) {
    for (const route of SNAPSHOT_ROUTES) {
      test(`${viewport.name} · ${route.slug}`, async ({ page, context, baseURL }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });

        if (!route.public) {
          await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
        }

        const ready = await gotoReadyShell(page, route);
        test.skip(!ready, "Auth redirect — snapshot skipped without session");

        await stabilizePageForScreenshot(page);

        await expect(page).toHaveScreenshot(`${viewport.name}-${route.slug}.png`, {
          fullPage: false,
          mask: [
            page.locator("time"),
            page.locator('[data-visual-mask="dynamic"]'),
          ],
        });
      });
    }
  }
});
