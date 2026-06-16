import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Analytics report artifact (DA5)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("report panel loads artifact and saves edits", async ({ page }) => {
    await page.goto("/apps-tools/analytics?section=report#analytics-report", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByTestId("analytics-report-artifact")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Signup funnel review" })).toBeVisible();
    await expect(page.getByTestId("analytics-report-artifact")).toContainText("Weekly active users");

    await page.getByRole("button", { name: "Edit" }).click();
    await page.getByTestId("analytics-report-markdown-editor").fill(
      "# Signup funnel\n\nOrganic dropped 18% week over week.\n\nOperator note added.",
    );
    await page.getByTestId("analytics-report-save").click();
    await expect(page.getByText("Report saved · v2")).toBeVisible({ timeout: 10_000 });
  });
});
