import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Journal studio overnight gardener (TJ3)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("gardener section shows pending draft with approve actions", async ({ page }) => {
    await page.goto("/apps-tools/trading-journal?section=gardener#journal-studio-gardener", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Journal" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("journal-studio-gardener-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Overnight gardener" })).toBeVisible();
    await expect(page.getByText("Wait for confirmation before sizing up")).toBeVisible();
    await expect(page.getByTestId("journal-draft-approve-draft-1")).toBeVisible();
    await expect(page.getByTestId("journal-gardener-run")).toBeVisible();
  });
});
