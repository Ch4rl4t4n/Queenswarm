import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("NP2 creative rubric on social publish (Riverflow)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("marketing automation publish section shows weighted creative rubric strip", async ({ page }) => {
    await page.goto("/apps-tools/marketing-automation?section=publish#social-publish", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Marketing automation" })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("#social-publish")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("publish-creative-rubric-strip")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Composition")).toBeVisible();
    await expect(page.getByText("82% overall")).toBeVisible();
  });
});
