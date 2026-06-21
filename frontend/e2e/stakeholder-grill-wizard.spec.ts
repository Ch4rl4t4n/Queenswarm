import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks, STUB_OPERATOR_ME } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Stakeholder Grill wizard (NP1)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    // Stakeholder Grill / Video Batch wizards are power tools surfaced outside Personal OS lite.
    // Override auth/me to the full (non-personal) operator so the Kanban wizard entry renders.
    await page.route("**/api/proxy/auth/me**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...STUB_OPERATOR_ME, personal_os_mode: false }),
      });
    });
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("mission kanban shows grill wizard entry", async ({ page }) => {
    await page.goto("/tasks?tab=board");
    await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole("heading", { name: "Grill my brief" })).toBeVisible();
    const triageInput = page.locator("input[placeholder*='New task title']");
    await triageInput.fill("Ship Gumroad hero pack listing with verified CTA");
    await page.waitForResponse(
      (res) => res.url().includes("mission-kanban/recipe-match") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByTestId("mission-kanban-recipe-match-panel")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("button", { name: "Use on dispatch" })).toBeVisible();
    await page.getByRole("button", { name: "Open wizard" }).click();
    await expect(page.getByText("Problem / opportunity", { exact: true })).toBeVisible();
    await expect(
      page.locator("#stakeholder-grill-wizard").getByText("Kill criteria", { exact: true }),
    ).toBeVisible();
  });
});
