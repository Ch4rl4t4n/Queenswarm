import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

test.describe("PWA shell — manifest + offline routes", () => {
  test("manifest.webmanifest is valid JSON with Queenswarm branding", async ({ request }) => {
    const res = await request.get("/manifest.webmanifest");
    expect(res.ok()).toBeTruthy();

    const body = (await res.json()) as { name?: string; display?: string; theme_color?: string };
    expect(body.name).toContain("Queenswarm");
    expect(body.display).toBe("standalone");
    expect(body.theme_color).toBeTruthy();
  });

  test("sw.js is served from public root", async ({ request }) => {
    const res = await request.get("/sw.js");
    expect(res.ok()).toBeTruthy();
    const text = await res.text();
    expect(text).toContain("queenswarm-shell");
  });

  test("mobile offline page renders shell copy", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/offline", { waitUntil: "load", timeout: 45_000 });
    await expect(page.getByRole("heading", { name: /hive offline/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /back to login/i })).toBeVisible();
  });

  test("tablet offline banner appears when navigator is offline", async ({ page, context, baseURL }) => {
    await installShellApiMocks(page);
    await page.setViewportSize({ width: 768, height: 1024 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    await page.goto("/swarms", { waitUntil: "load", timeout: 60_000 });
    await expect(page.locator('[data-hive-shell="canvas"]').first()).toBeVisible({ timeout: 45_000 });

    await context.setOffline(true);
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));

    await expect(page.locator(".hive-offline-banner")).toBeVisible({ timeout: 10_000 });

    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect(page.locator(".hive-offline-banner")).toBeHidden({ timeout: 10_000 });
  });
});

test.describe("PWA shell — install prompt", () => {
  test.beforeEach(async ({ page }) => {
    await installShellApiMocks(page);
  });

  test("mobile shows install prompt after second visit", async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.setItem("qs_pwa_visits", "2");
      localStorage.removeItem("qs_pwa_install_dismissed");
      sessionStorage.removeItem("qs_pwa_visit_bumped");
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.goto("/swarms", { waitUntil: "load", timeout: 60_000 });

    await expect(page.locator("[data-hive-install-prompt]")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /not now|teraz nie/i })).toBeVisible();
  });

  test("desktop never shows install prompt", async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.setItem("qs_pwa_visits", "5");
      localStorage.removeItem("qs_pwa_install_dismissed");
      sessionStorage.removeItem("qs_pwa_visit_bumped");
    });

    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.goto("/swarms", { waitUntil: "load", timeout: 60_000 });

    await expect(page.locator("[data-hive-install-prompt]")).toHaveCount(0);
  });

  test("dismiss hides install prompt for session", async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.setItem("qs_pwa_visits", "3");
      localStorage.removeItem("qs_pwa_install_dismissed");
      sessionStorage.removeItem("qs_pwa_visit_bumped");
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.goto("/tasks", { waitUntil: "load", timeout: 60_000 });

    const prompt = page.locator("[data-hive-install-prompt]");
    await expect(prompt).toBeVisible({ timeout: 15_000 });
    await page.getByRole("button", { name: /not now|teraz nie/i }).click();
    await expect(prompt).toBeHidden({ timeout: 10_000 });
  });
});
