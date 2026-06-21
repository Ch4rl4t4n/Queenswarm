import { expect, test } from "@playwright/test";

import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const missionKanbanE2eEnabled = process.env.E2E_MISSION_KANBAN === "1";

test.describe("mission kanban", () => {
  test.beforeEach(() => {
    test.skip(!missionKanbanE2eEnabled, "Set E2E_MISSION_KANBAN=1 to run mission kanban UI checks.");
  });

  test.beforeEach(async ({ page }) => {
    await maybeInstallShellApiMocks(page);
    await suppressPwaInstallPrompt(page);
  });

  test("done task supports edit and clear-all delete", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    await page.goto("/tasks?tab=board", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Content week")).toBeVisible({ timeout: 30_000 });

    const doneCard = page.locator("li").filter({ hasText: "Content week" });
    await expect(doneCard.getByTitle("Edit task")).toBeVisible();
    await expect(doneCard.getByTitle("Remove task")).toBeVisible();
    await expect(page.getByRole("button", { name: "Clear all" })).toBeVisible();

    await doneCard.getByTitle("Remove task").click();
    await expect(page.getByRole("heading", { name: "Remove task?" })).toBeVisible();
    await page.getByRole("button", { name: "Remove", exact: true }).click();
    await expect(page.getByText("Content week")).toBeHidden({ timeout: 10_000 });
  });
});
