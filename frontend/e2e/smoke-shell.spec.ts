import { test, expect } from "@playwright/test";

test.describe("hive public shell smoke", () => {
  test("login page exposes Queenswarm gate", async ({ page }) => {
    await page.goto("/login", { waitUntil: "load", timeout: 45_000 });
    await expect(page.getByText("Queenswarm", { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Welcome back/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /continue/i })).toBeVisible();
  });

  test("unauthenticated dashboard root redirects toward login gate", async ({ page }) => {
    await page.goto("/", { waitUntil: "commit", timeout: 45_000 });
    await expect(page).toHaveURL(/\/login/, { timeout: 45_000 });
  });

  test("ballroom route resolves behind auth redirect", async ({ page }) => {
    await page.goto("/ballroom", { waitUntil: "load", timeout: 45_000 });
    await expect(page).toHaveURL(/\/(login|ballroom)/, { timeout: 45_000 });
  });
});
