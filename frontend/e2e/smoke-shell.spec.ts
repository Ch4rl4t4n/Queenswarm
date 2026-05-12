import { test, expect } from "@playwright/test";

test.describe("hive public shell smoke", () => {
  test("login page exposes QueenSwarm gate", async ({ page }) => {
    await page.goto("/login", { waitUntil: "load", timeout: 45_000 });
    await expect(page.getByText("QueenSwarm", { exact: true })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("heading", { name: /Welcome back/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Continue/i })).toBeVisible();
  });

  test("unauthenticated dashboard root redirects toward login gate", async ({ page }) => {
    await page.goto("/", { waitUntil: "commit", timeout: 45_000 });
    await expect(page).toHaveURL(/\/login/, { timeout: 45_000 });
  });
});
