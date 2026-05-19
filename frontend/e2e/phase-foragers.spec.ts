import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const foragersE2eEnabled = process.env.E2E_FORAGERS === "1";

test.describe("foragers page", () => {
  test.beforeEach(() => {
    test.skip(!foragersE2eEnabled, "Set E2E_FORAGERS=1 to run foragers UI checks.");
  });

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("foragers dashboard renders dynamic controls and create modal", async ({ page }) => {
    await page.goto("/foragers", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Foragers" })).toBeVisible({ timeout: 30_000 });
    const createButton = page.getByRole("button", { name: /\+ Create new Forager/i });
    await expect(createButton).toBeVisible();
    await expect(page.getByText("Manual ingest payload")).toBeVisible();

    await createButton.click();
    await expect(page.getByRole("heading", { name: /Create forager/i })).toBeVisible();
    await expect(page.getByText("Name", { exact: true })).toBeVisible();
    await expect(page.getByText("Type", { exact: true })).toBeVisible();
    await expect(page.getByText("Source config (JSON)", { exact: true })).toBeVisible();
    await expect(page.getByText("Frequency and routine", { exact: true })).toBeVisible();
  });
});
