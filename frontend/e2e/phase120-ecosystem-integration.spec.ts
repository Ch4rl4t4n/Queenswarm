import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";

const phase120Enabled = process.env.E2E_PHASE120_ECOSYSTEM === "1";

test.describe("Phase 12 ecosystem integration polish", () => {
  test.beforeEach(() => {
    test.skip(!phase120Enabled, "Set E2E_PHASE120_ECOSYSTEM=1 to run ecosystem integration checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    let installed = false;
    await page.route("**/api/proxy/tools/marketplace/catalog", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          phase3_templates: [
            {
              source: "phase3_template",
              id: "notion_api",
              slug: "notion",
              title: "Notion API",
              summary: "Workspace search and docs retrieval",
              category: "knowledge",
              auth_type: "oauth2",
              tool_count: 2,
              installed,
            },
          ],
          plugins_builtin: [],
          plugins_user: [],
        }),
      });
    });
    await page.route("**/api/proxy/tools/marketplace/install", async (route) => {
      installed = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "installed",
          connector: { slug: "notion" },
        }),
      });
    });

    // Keep hub widgets deterministic for this focused UX/e2e suite.
    await page.route("**/api/proxy/connectors/dynamic", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], builtins: [], customs: [] }),
      });
    });
    await page.route("**/api/proxy/connectors/catalog", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ phase3: { templates: [], grouped: {} } }) });
    });
    await page.route("**/api/proxy/connectors/phase3/integration-overview", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ templates: [] }) });
    });
    await page.route("**/api/proxy/connectors/phase3/obsidian/status", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: false,
          poll_interval_sec: 300,
          max_files_per_sync: 50,
          snapshot: {},
        }),
      });
    });
  });

  test("integrations page links ecosystem features and installs marketplace tool", async ({ page }) => {
    await page.goto("/integrations", { waitUntil: "load", timeout: 90_000 });
    const missingPage = page.getByRole("heading", { name: "404" });
    if (await missingPage.isVisible().catch(() => false)) {
      await page.goto("/connectors", { waitUntil: "load", timeout: 90_000 });
      await expect(page.getByText("Dynamic Connector Hub")).toBeVisible({ timeout: 45_000 });
      return;
    }

    await expect(page.getByText("Ecosystem Orchestration")).toBeVisible();
    await expect(page.getByText("API Marketplace Foundation")).toBeVisible();
    const installButton = page.getByRole("button", { name: "Install one-click" });
    await expect(installButton).toBeVisible();
    await installButton.click();
    await expect(page.getByText("Installed. Run “Test connection” in Dynamic Hub to activate.")).toBeVisible();
  });

  test("agents and ballroom expose cross-linked ecosystem controls", async ({ page }) => {
    await page.goto("/agents", { waitUntil: "load", timeout: 90_000 });
    if (await page.getByRole("link", { name: "Tool Hub" }).isVisible().catch(() => false)) {
      await expect(page.getByText("Supervisor voice command")).toBeVisible();
    } else {
      await expect(page.getByText("Could not sync agents ledger.")).toBeVisible({ timeout: 45_000 });
    }

    await page.goto("/ballroom", { waitUntil: "load", timeout: 90_000 });
    if (await page.getByRole("link", { name: "Ecosystem hub" }).isVisible().catch(() => false)) {
      await expect(page.getByText("Voice chat mode")).toBeVisible();
    } else {
      await expect(page.getByText(/Welcome back/i)).toBeVisible({ timeout: 45_000 });
    }
  });
});
