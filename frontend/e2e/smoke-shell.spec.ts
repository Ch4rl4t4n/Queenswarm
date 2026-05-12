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

  test("agents surface resolves (login gate or shell)", async ({ page }) => {
    await page.goto("/agents", { waitUntil: "load", timeout: 45_000 });
    await expect(page).toHaveURL(/\/(login|agents)/, { timeout: 45_000 });
  });

  test("tasks backlog route resolves behind auth redirect", async ({ page }) => {
    await page.goto("/tasks", { waitUntil: "load", timeout: 45_000 });
    await expect(page).toHaveURL(/\/(login|tasks)/, { timeout: 45_000 });
  });
});

