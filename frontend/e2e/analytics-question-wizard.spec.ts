import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics question wizard (DA4)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("question wizard loads, previews, and dispatches brief", async ({ page }) => {
    await page.goto("/apps-tools/analytics?section=question#analytics-question", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("analytics-question-wizard")).toBeVisible({ timeout: 15_000 });

    const input = page.getByTestId("analytics-question-input");
    await input.fill("Why did organic signups drop 18% week over week in May?");
    await expect(page.getByTestId("analytics-question-preview")).toBeVisible({ timeout: 10_000 });

    await page.getByTestId("analytics-question-submit").click();
    await expect(page.getByTestId("analytics-question-wizard")).toContainText("Analytics session started", {
      timeout: 10_000,
    });
  });
});
