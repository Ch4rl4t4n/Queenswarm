import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

test.describe("Automation Ladder journeys", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await installShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("Agents sessions shows Automation Ladder panel", async ({ page }) => {
    await page.goto("/agents#sessions", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByTestId("automation-ladder-panel")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("automation-ladder-panel")).toContainText("L1");
    await expect(page.getByTestId("automation-ladder-panel")).toContainText("L5");
  });

  test("Knowledge recipes opens Schedule routine dialog and creates routine", async ({ page }) => {
    await page.goto("/knowledge#recipes", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const recipesNav = page.getByRole("navigation", { name: "Knowledge sections" });
    await expect(recipesNav).toBeVisible({ timeout: 45_000 });
    await recipesNav.getByRole("button", { name: /Recipes · Learning/i }).click();

    await expect(page.locator("#recipes")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("heading", { name: "Lead Gen Lane" })).toBeVisible({ timeout: 45_000 });

    const scheduleBtn = page.getByTestId("recipe-schedule-routine").first();
    await expect(scheduleBtn).toBeEnabled();
    await scheduleBtn.click();

    const dialog = page.getByRole("dialog", { name: "Schedule as routine" });
    await expect(dialog).toBeVisible({ timeout: 15_000 });
    await expect(dialog.getByRole("heading", { name: "Schedule as routine" })).toBeVisible();

    await dialog.getByRole("button", { name: "Schedule routine" }).click();
    await expect(dialog.getByText("Routine created")).toBeVisible({ timeout: 20_000 });
    await expect(dialog.getByText("recipe-lead-gen-lane")).toBeVisible();
  });
});
