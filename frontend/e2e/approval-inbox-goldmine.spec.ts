import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Approval inbox goldmine strip (DG3)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("business cockpit shows goldmine delta strip in approval inbox", async ({ page }) => {
    await page.goto("/agentic-os", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("button", { name: /^Business$/i }).click({ timeout: 15_000 });
    await page.waitForResponse(
      (res) => res.url().includes("operator/approvals") && res.status() === 200,
      { timeout: 15_000 },
    );
    await expect(page.getByText("Approval inbox", { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("approval-inbox-goldmine-strip")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("E2E YouTube Intel")).toBeVisible();
  });
});
