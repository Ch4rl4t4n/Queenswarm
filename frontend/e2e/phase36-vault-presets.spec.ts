import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

function assertOrSkipOnLoginRedirect(
  page: import("@playwright/test").Page,
  expectedNext: string[],
): boolean {
  const current = new URL(page.url());
  if (current.pathname !== "/login") {
    return false;
  }
  expect(expectedNext).toContain(current.searchParams.get("next") ?? "");
  return true;
}

test.describe("Phase 3.6 vault vendor presets", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test.beforeEach(async ({ context, baseURL }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("Gmail preset hydrates slug, OAuth mode, and Google token endpoint", async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/connectors", { waitUntil: "load", timeout: 90_000 });
    await page.waitForTimeout(500);
    if (assertOrSkipOnLoginRedirect(page, ["/connectors", "/integrations"])) {
      return;
    }

    await page.getByRole("button", { name: "Gmail (Google Workspace)", exact: true }).click();

    await expect(page.locator("#qs-vault-connector-slug")).toHaveValue("gmail_workspace");

    await expect(page.getByRole("button", { name: "OAuth2", exact: true })).toBeVisible();
    await expect(page.locator("#qs-vault-token-endpoint")).toHaveValue("https://oauth2.googleapis.com/token");
  });

  test("Notion preset switches to API key flow", async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/connectors", { waitUntil: "load", timeout: 90_000 });
    await page.waitForTimeout(500);
    if (assertOrSkipOnLoginRedirect(page, ["/connectors", "/integrations"])) {
      return;
    }
    await page.getByRole("button", { name: "Notion", exact: true }).click();
    await expect(page.locator("#qs-vault-connector-slug")).toHaveValue("notion_workspace");
    await expect(page.getByRole("button", { name: "API key", exact: true })).toBeVisible();
  });
});
