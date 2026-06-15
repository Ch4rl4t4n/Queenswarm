import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const STUB_OVERVIEW = {
  policy: { auto_spawn_auto_approve_enabled: false },
  kpis: {
    foragers_total: 1,
    foragers_active: 1,
    foragers_paused: 0,
    foragers_error: 0,
    items_ingested_24h: 3,
    items_trend_pct: null,
    hivemind_chunks_7d: 1,
    auto_spawned_bees: 0,
  },
  configurations: [
    {
      id: "e2e-forager-feedback-1",
      source_name: "E2E Feedback Forager",
      source_type: "rss",
      schedule_label: "every 24h",
      last_run_seconds_ago: 120,
      items_count: 1,
      run_progress_pct: 100,
      status: "ok",
      is_active: true,
    },
  ],
};

test.describe("Forager hit feedback (DG4)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
    await page.route("**/api/proxy/dashboard/foragers-overview**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(STUB_OVERVIEW),
      });
    });
  });

  test("forager results dialog records thumbs-up feedback", async ({ page }) => {
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Results" }).click();
    await expect(page.getByRole("heading", { name: "Forager results" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("forager-hit-feedback")).toBeVisible();
    await page.getByTestId("forager-hit-feedback-up").click();
    await page.waitForResponse(
      (res) => res.url().includes("hit-feedback") && res.status() === 200,
      { timeout: 15_000 },
    );
  });
});
