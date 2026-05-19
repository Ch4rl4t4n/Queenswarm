import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const dynamicTemplatesE2eEnabled = process.env.E2E_AGENT_TEMPLATES === "1";

test.describe("dynamic agent templates page", () => {
  test.beforeEach(() => {
    test.skip(!dynamicTemplatesE2eEnabled, "Set E2E_AGENT_TEMPLATES=1 to run dynamic template UI checks.");
  });

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("agents/new renders template library controls", async ({ page }) => {
    await page.goto("/agents/new", { waitUntil: "load", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Spawn agent" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Template library", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /\+ Create new template/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Custom \(blank\)/i })).toBeVisible();
  });
});
