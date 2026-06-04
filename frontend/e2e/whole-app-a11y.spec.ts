import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eHiveHomePath } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";

async function gotoShellRoute(
  page: import("@playwright/test").Page,
  path: string,
  options?: { waitForMobileNav?: boolean },
): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await expect(page.locator('[data-hive-shell="canvas"], main').first()).toBeVisible({ timeout: 45_000 });
  if (options?.waitForMobileNav) {
    await expect(page.getByRole("navigation", { name: "Primary mobile navigation" })).toBeVisible({
      timeout: 20_000,
    });
  }
}

test.describe("Whole-App a11y — shell keyboard", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("skip link focuses main canvas on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoShellRoute(page, e2eHiveHomePath(), { waitForMobileNav: true });

    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: /Skip to main content/i });
    await expect(skip).toBeFocused({ timeout: 15_000 });

    await skip.click();
    await expect(page.locator("#hive-main-canvas")).toBeFocused();
  });

  test("mobile nav drawer closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoShellRoute(page, e2eHiveHomePath(), { waitForMobileNav: true });

    const menuButton = page.getByRole("button", { name: "Open navigation menu" });
    await expect(menuButton).toBeVisible({ timeout: 15_000 });
    await menuButton.click();
    const drawer = page.locator(".hive-sidebar-rail--mobile.hive-sidebar-rail--mobile-open");
    await expect(drawer).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.locator(".hive-sidebar-rail--mobile")).toHaveClass(/hive-sidebar-rail--mobile-closed/, {
      timeout: 10_000,
    });
  });

  test("more sheet closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoShellRoute(page, "/swarms", { waitForMobileNav: true });

    const more = page.getByRole("button", { name: "More" });
    await expect(more).toBeVisible({ timeout: 15_000 });
    await more.click();
    await expect(page.getByRole("dialog", { name: /Hive navigation/i })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: /Hive navigation/i })).toHaveCount(0, { timeout: 10_000 });
  });

  test("bottom nav more button exposes aria-expanded", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoShellRoute(page, "/tasks", { waitForMobileNav: true });

    const more = page.getByRole("button", { name: "More" });
    await expect(more).toHaveAttribute("aria-expanded", "false");

    await more.click();
    await expect(more).toHaveAttribute("aria-expanded", "true");
  });
});

test.describe("Whole-App a11y — panels and subnav", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("settings section subnav moves focus with arrow keys", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/settings/security");

    const sectionsNav = page.getByRole("navigation", { name: "Settings sections" });
    await expect(sectionsNav).toBeVisible({ timeout: 15_000 });

    const securityTab = sectionsNav.getByRole("link", { name: "Security" });
    const llmTab = sectionsNav.getByRole("link", { name: "LLM & voice" });
    await securityTab.focus();

    // Essentials order: Security → Notifications → LLM & voice (custom tab order may differ).
    for (let step = 0; step < 4; step += 1) {
      await page.keyboard.press("ArrowRight");
      try {
        await expect(page).toHaveURL(/\/settings\/llm-keys/, { timeout: 2_000 });
        break;
      } catch {
        if (step === 3) {
          throw new Error("Arrow keys did not reach LLM & voice tab");
        }
      }
    }

    await expect(page).toHaveURL(/\/settings\/llm-keys/, { timeout: 10_000 });
    await expect(llmTab).toHaveAttribute("aria-current", "page");
    await expect(llmTab).toBeFocused({ timeout: 5_000 });
  });

  test("settings costs route exposes single page h1", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/settings/costs");

    await expect(page.getByTestId("hive-page-shell").locator("h1")).toHaveText("Settings");
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.getByRole("heading", { name: "Costs", level: 2 })).toBeVisible({ timeout: 15_000 });
  });

  test("info hint dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/swarms");

    const hint = page.getByRole("button", { name: /Info: Swarms/i }).first();
    await hint.click();
    await expect(page.getByRole("dialog").filter({ hasText: /Swarms/i })).toBeVisible({ timeout: 10_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog").filter({ hasText: /Swarms/i })).toHaveCount(0, { timeout: 10_000 });
  });

  test("2FA enroll dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/settings/security");

    await page.getByRole("button", { name: "Set up 2FA" }).click();
    await expect(page.getByRole("dialog", { name: "Confirm password" })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Confirm password" })).toHaveCount(0, { timeout: 10_000 });
  });

  test("API keys mint dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/settings/api-keys");

    await page.getByRole("button", { name: "Mint script key" }).click();
    await expect(page.getByRole("dialog", { name: "New script slug" })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "New script slug" })).toHaveCount(0, { timeout: 10_000 });
  });

  test("swarms new colony dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/swarms");

    await page.getByRole("button", { name: "New colony" }).click();
    await expect(page.getByRole("dialog", { name: "New colony" })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "New colony" })).toHaveCount(0, { timeout: 10_000 });
  });

  test("forager create dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/foragers");

    await page.getByRole("button", { name: "New forager" }).click();
    await expect(page.getByRole("dialog", { name: "Create forager" })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Create forager" })).toHaveCount(0, { timeout: 10_000 });
  });

  test("agents template editor dialog closes on Escape", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoShellRoute(page, "/agents/new");

    await page.getByRole("button", { name: "+ Create new template" }).click();
    await expect(page.getByRole("dialog", { name: "Create template" })).toBeVisible({ timeout: 15_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Create template" })).toHaveCount(0, { timeout: 10_000 });
  });
});
