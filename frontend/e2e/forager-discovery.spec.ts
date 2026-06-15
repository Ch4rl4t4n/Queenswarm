import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Forager discovery wizard (DG6)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("foragers page shows discovery wizard with search and bind", async ({ page }) => {
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("forager-discovery-panel")).toBeVisible({ timeout: 10_000 });

    const textarea = page.getByPlaceholder(/EU python job board RSS feed/i);
    await textarea.fill("EU python job board RSS");
    await page.getByRole("button", { name: "Discover" }).click();

    await page.waitForResponse(
      (res) => res.url().includes("discovery-wizard/search") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByText("Example jobs feed")).toBeVisible();
    await page.getByRole("button", { name: "Bind 1 URL" }).click();

    await page.waitForResponse(
      (res) => res.url().includes("discovery-wizard/bind") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByText(/Discovery URLs bound/i)).toBeVisible({ timeout: 10_000 });
  });
});
