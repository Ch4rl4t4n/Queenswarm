import { test, expect } from "@playwright/test";

/**
 * Phase 2.7 smoke — navigation gates and mobile viewport sanity without authenticated cookies.
 */

test.describe("Phase 2.7 navigation smoke", () => {
  test("mobile viewport login gate renders primary controls", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login", { waitUntil: "load", timeout: 45_000 });
    await expect(page.getByRole("button", { name: /continue/i })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/nectar key/i)).toBeVisible();
  });

  test("protected hive routes redirect unauthenticated users to login", async ({ page }) => {
    const paths = [
      "/connectors",
      "/learning",
      "/jobs",
      "/external-projects",
      "/tasks",
      "/workflows",
      "/hive-mind",
      "/outputs",
      "/recipes",
    ];
    for (const path of paths) {
      await page.goto(path, { waitUntil: "load", timeout: 45_000 });
      await expect(page).toHaveURL(/\/login/, { timeout: 45_000 });
    }
  });
});
