import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const E2E_GOLDMINE_ALERT_ROW = {
  enabled: true,
  alerts: [
    {
      forager_id: "e2e-forager-goldmine-1",
      forager_name: "E2E YouTube Intel",
      source_type: "youtube",
      new_item_count: 3,
      since_iso: "2026-06-04T12:00:00Z",
      headline: "3 new signals since last run",
      skill_bundle: ["competitor-scrape-analyze", "context", "research"],
      preview_items: [
        {
          id: "e2e-preview-1",
          title: "Competitor launch recap",
          scraped_at: "2026-06-05T08:00:00Z",
          source_url: "https://youtube.com/watch?v=e2e",
        },
      ],
    },
  ],
  operator_hint: "Dispatch attaches a skill bundle and parks triage on Mission Kanban.",
};

test.describe("Forager goldmine dispatch (DG7)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("foragers page shows goldmine alert strip with dispatch", async ({ page }) => {
    await page.route("**/api/v1/dashboard/forager-goldmine-alerts**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(E2E_GOLDMINE_ALERT_ROW),
      });
    });
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    await page.waitForResponse(
      (res) => res.url().includes("forager-goldmine-alerts") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByTestId("forager-goldmine-alerts-panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("E2E YouTube Intel")).toBeVisible();
    await expect(page.getByRole("button", { name: "Dispatch" })).toBeVisible();
    await expect(page.getByText("competitor-scrape-analyze")).toBeVisible();
  });
});
