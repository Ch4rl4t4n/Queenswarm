import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

test.describe("Broker MCP Robinhood (RA1/RA2)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("trading automation broker MCP section shows checklist and probe", async ({ page }) => {
    await page.goto("/apps-tools/trading-automation?section=mcp#broker-mcp", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await expect(page.getByRole("heading", { name: "Trading Automation" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("broker-mcp-panel")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Broker MCP — Robinhood Agentic" })).toBeVisible();
    await expect(page.getByTestId("broker-mcp-checklist")).toBeVisible();
    await expect(page.getByTestId("broker-mcp-checklist").getByText("Complete Robinhood OAuth")).toBeVisible();
    await expect(page.getByText("agent.robinhood.com/mcp/trading")).toBeVisible();
  });
});
