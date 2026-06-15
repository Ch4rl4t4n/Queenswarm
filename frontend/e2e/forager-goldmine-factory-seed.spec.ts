import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const STUB_ALERTS = {
  enabled: true,
  alerts: [
    {
      forager_id: "e2e-forager-goldmine-1",
      forager_name: "E2E YouTube Intel",
      source_type: "youtube",
      new_item_count: 3,
      since_iso: "2026-06-05T10:00:00Z",
      headline: "3 new",
      skill_bundle: ["competitor-scrape-analyze", "context", "research"],
      preview_items: [
        { id: "k1", title: "New channel video on AI agents", source_url: "https://youtube.com/watch?v=1" },
      ],
    },
  ],
  operator_hint: "Dispatch or seed Factory.",
};

test.describe("Goldmine factory seed (DG8)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
    await page.route("**/api/proxy/dashboard/forager-goldmine-alerts**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_ALERTS),
      });
    });
  });

  test("foragers goldmine panel shows factory seed action", async ({ page }) => {
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("forager-goldmine-alerts-panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Factory seed" })).toBeVisible();
    await page.getByRole("button", { name: "Factory seed" }).click();
    await page.waitForResponse(
      (res) => res.url().includes("goldmine-factory-seed/submit") && res.status() === 201,
      { timeout: 15_000 },
    );
  });
});
