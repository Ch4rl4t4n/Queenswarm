import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

/**
 * Mission Control gold standard: sub-section menu bar (Dnes | Board | Schvalenia
 * | Vysledky) + Jarvis "Do this" acting in place (no jump to a dead section).
 */
test.describe("Mission Control sub-sections", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await suppressPwaInstallPrompt(page);
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("Dnes is default, Jarvis 'Do this' acts in place, tabs switch sub-section", async ({ page }) => {
    await page.goto("/tasks", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({ timeout: 30_000 });

    // Default sub-section "Dnes" -> Jarvis advisor with a "Do this" affordance.
    await expect(page.getByTestId("mission-home-jarvis-advisor")).toBeVisible({ timeout: 20_000 });
    const doThis = page.getByTestId("mission-home-jarvis-do-this").first();
    await expect(doThis).toBeVisible();

    // A verify "Do this" must act in place — stay on /tasks, never navigate away.
    await doThis.click();
    await expect(page).toHaveURL(/\/tasks(\?|#|$)/, { timeout: 5_000 });

    // Schvalenia sub-section shows the real, actionable approval inbox.
    await page.getByTestId("section-tab-approvals").click();
    await expect(page).toHaveURL(/tab=approvals/, { timeout: 5_000 });
    await expect(page.getByText("Goldmine · E2E YouTube Intel · 3 new")).toBeVisible({ timeout: 20_000 });

    // Vysledky sub-section renders the result panel.
    await page.getByTestId("section-tab-results").click();
    await expect(page).toHaveURL(/tab=results/, { timeout: 5_000 });
    await expect(page.getByTestId("mission-results-panel")).toBeVisible({ timeout: 20_000 });

    // Board sub-section switches the workspace.
    await page.getByTestId("section-tab-board").click();
    await expect(page).toHaveURL(/tab=board/, { timeout: 5_000 });
  });
});
