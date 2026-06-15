import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Stakeholder Grill wizard (NP1)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("mission kanban shows grill wizard entry", async ({ page }) => {
    await page.goto("/tasks");
    await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole("heading", { name: "Grill my brief" })).toBeVisible();
    await page.getByRole("button", { name: "Open wizard" }).click();
    await expect(page.getByText("Problem / opportunity", { exact: true })).toBeVisible();
    await expect(
      page.locator("#stakeholder-grill-wizard").getByText("Kill criteria", { exact: true }),
    ).toBeVisible();
  });
});
