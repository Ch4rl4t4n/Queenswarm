import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";

test.describe("Whole-App Settings — panel density", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("capabilities atlas collapses advanced sections by default", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/capabilities", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const panel = page.getByTestId("settings-capabilities-panel");
    await expect(panel).toBeVisible({ timeout: 45_000 });
    await expect(panel.getByRole("heading", { name: "Live features" })).toBeVisible();

    const missionToggle = panel.getByRole("button", { name: /North Star & rollout/i });
    await expect(missionToggle).toHaveAttribute("aria-expanded", "false");

    const archToggle = panel.getByRole("button", { name: /Backend \+ Frontend stack/i });
    await expect(archToggle).toHaveAttribute("aria-expanded", "false");
  });

  test("capabilities hash deep-link expands architecture section", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/capabilities#capabilities-architecture", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });

    const panel = page.getByTestId("settings-capabilities-panel");
    await expect(panel).toBeVisible({ timeout: 45_000 });

    const archToggle = panel.getByRole("button", { name: /Backend \+ Frontend stack/i });
    await expect(archToggle).toHaveAttribute("aria-expanded", "true", { timeout: 15_000 });
  });

  test("harness operator loops keeps trio open and collapses slack trainer", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/settings/harness#rules-loops", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const loops = page.getByTestId("settings-harness-loops");
    await expect(loops).toBeVisible({ timeout: 45_000 });

    const trioToggle = loops.getByRole("button", { name: /My 3 Bees trio/i });
    await expect(trioToggle).toHaveAttribute("aria-expanded", "true");

    const slackToggle = loops.getByRole("button", { name: /Slack harness trainer/i });
    if ((await slackToggle.count()) > 0) {
      await expect(slackToggle).toHaveAttribute("aria-expanded", "false");
    }
  });
});
