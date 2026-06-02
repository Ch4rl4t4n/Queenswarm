import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const enabled = process.env.E2E_HARNESS_SELF_IMPROVE === "1";

test.describe("Harness self-improve smoke (Four Cs + Innovation viability)", () => {
  test.skip(!enabled, "Set E2E_HARNESS_SELF_IMPROVE=1");

  test.beforeEach(async ({ page, context, baseURL }) => {
    await installShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("Four Cs audit panel renders in harness rules overview", async ({ page }) => {
    await page.goto("/settings/harness#rules", { waitUntil: "domcontentloaded", timeout: 60_000 });
    const rulesNav = page.getByRole("navigation", { name: "Harness sections" });
    await expect(rulesNav).toBeVisible({ timeout: 45_000 });
    await rulesNav.getByRole("button", { name: /Rules & skills/i }).click();
    await expect(page.getByRole("heading", { name: /Four Cs readiness/i })).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Context/i).first()).toBeVisible();
    await expect(page.getByText(/Queen Maintainer pre-tool safety/i)).toBeVisible();
  });

  test("Innovation Lab shows viability banner and Approve & queue", async ({ page }) => {
    await page.goto("/agentic-os#innovation", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Brainstorm → approve/i })).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.getByTestId("innovation-viability-banner")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("button", { name: /Approve & queue/i })).toBeVisible();
  });
});
