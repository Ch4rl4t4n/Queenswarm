import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

test.describe("Whole-App IA — primary sidebar order", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("desktop sidebar follows canonical zone order when CP enabled", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "CP IA applies only when operator control plane is enabled");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/security", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const nav = page.locator('nav[aria-label="Hive navigation"]');
    await expect(nav).toBeVisible({ timeout: 45_000 });

    const labels = await nav.locator(".hive-nav-label").allTextContents();
    const trimmed = labels.map((t) => t.trim()).filter(Boolean);

    expect(trimmed.indexOf("Agentic OS")).toBeLessThan(trimmed.indexOf("Apps & Tools"));
    expect(trimmed.indexOf("Apps & Tools")).toBeLessThan(trimmed.indexOf("Integrations"));
    expect(trimmed.indexOf("Integrations")).toBeLessThan(trimmed.indexOf("Knowledge"));
    expect(trimmed.filter((l) => l === "Settings")).toHaveLength(1);
    expect(trimmed).not.toContain("Factory");
    expect(trimmed).not.toContain("Foragers");
  });
});
