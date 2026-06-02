import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import {
  AGENTS_LANE_CROSS_LINKS,
  EXECUTION_LANE_CROSS_LINKS,
  FACTORY_CONTENT_FACTORY_CROSS_LINKS,
  LEGACY_INTEGRATIONS_REDIRECTS,
  LEGACY_KNOWLEDGE_REDIRECTS,
  LEGACY_ROUTE_REDIRECTS,
  urlMatchesLegacyRedirect,
} from "../lib/dead-button-audit";
import { EXECUTION_LANE_CROSS_LINK_LABELS } from "../lib/execution-lane-routes";
import { FACTORY_CROSS_LINK_LABELS } from "../lib/factory-content-factory-routes";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "../lib/feature-flags";

const CP_OPTIONAL_LEGACY = new Set(["/dashboard", "/costs", "/connectors", "/plugins", "/external-projects", "/hive-mind", "/outputs", "/recipes", "/learning", "/execution", "/hierarchy"]);

test.describe("Whole-App dead-button audit — legacy routes", () => {
  test.setTimeout(60_000);

  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
  });

  test("agentic-os renders page shell", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/agentic-os", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const shell = page.getByTestId("hive-page-shell");
    await expect(shell).toBeVisible({ timeout: 45_000 });
    await expect(shell.locator("h1")).toHaveText("Agentic OS");
  });

  test("legacy /cockpit preserves hash on redirect to agentic-os", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/cockpit#icm", { waitUntil: "domcontentloaded", timeout: 60_000 });

    await expect(page).toHaveURL(/\/agentic-os#icm/, { timeout: 45_000 });
    await expect(page.getByTestId("hive-page-shell")).toBeVisible();
  });

  for (const [legacy, target] of Object.entries(LEGACY_ROUTE_REDIRECTS)) {
    test(`${legacy} resolves to ${target}`, async ({ page }) => {
      test.skip(!OPERATOR_CONTROL_PLANE_ENABLED && !CP_OPTIONAL_LEGACY.has(legacy), "CP routes only");

      await page.goto(legacy, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await expect
        .poll(() => urlMatchesLegacyRedirect(page.url(), target), { timeout: 45_000 })
        .toBe(true);
    });
  }

  test("legacy /settings/billing redirects to costs billing plans hash", async ({ page }) => {
    await page.goto("/settings/billing", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page).toHaveURL(/\/settings\/costs#billing-plans/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { name: "Costs", level: 2 })).toBeVisible({ timeout: 45_000 });
  });

  test("costs ↔ enterprise cross-links resolve", async ({ page }) => {
    await page.goto("/settings/costs", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.getByRole("link", { name: /Open enterprise settings/i }).click();
    await expect(page).toHaveURL(/\/settings\/enterprise/, { timeout: 45_000 });
    await expect(page.getByRole("link", { name: /View spend cockpit/i })).toBeVisible({ timeout: 15_000 });

    await page.getByRole("link", { name: /View spend cockpit/i }).click();
    await expect(page).toHaveURL(/\/settings\/costs/, { timeout: 45_000 });
  });

  test("apps-tools module index deep-links to Marketing Automation", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/apps-tools", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByText("Module index")).toBeVisible({ timeout: 30_000 });

    const marketingCard = page.locator("article").filter({
      has: page.getByText("Marketing Automation", { exact: true }),
    });
    await expect(marketingCard).toBeVisible({ timeout: 30_000 });
    await marketingCard.getByRole("link", { name: "Configure" }).click();
    await expect(page).toHaveURL(/\/apps-tools\/marketing-automation/, { timeout: 45_000 });
  });

  test("integrations legacy /connectors lands on hub tab", async ({ page }) => {
    await page.goto("/connectors", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect
      .poll(() => urlMatchesLegacyRedirect(page.url(), LEGACY_INTEGRATIONS_REDIRECTS["/connectors"]), { timeout: 45_000 })
      .toBe(true);
    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible({ timeout: 45_000 });
  });

  test("knowledge legacy /hive-mind preserves hivemind hash", async ({ page }) => {
    await page.goto("/hive-mind", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect
      .poll(() => urlMatchesLegacyRedirect(page.url(), LEGACY_KNOWLEDGE_REDIRECTS["/hive-mind"]), { timeout: 45_000 })
      .toBe(true);
    await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible({ timeout: 45_000 });
  });

  test("content-factory ↔ factory blueprint cross-links resolve", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/apps-tools/content-factory", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Content Factory" })).toBeVisible({ timeout: 30_000 });

    const toBlueprint = FACTORY_CONTENT_FACTORY_CROSS_LINKS.find((row) => row.from === "/apps-tools/content-factory");
    expect(toBlueprint).toBeDefined();
    await page.getByRole("link", { name: FACTORY_CROSS_LINK_LABELS.toBlueprint }).click();
    await expect(page).toHaveURL(/\/factory/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Micro-SaaS Factory" })).toBeVisible({ timeout: 30_000 });

    const toModule = FACTORY_CONTENT_FACTORY_CROSS_LINKS.find((row) => row.from === "/factory");
    expect(toModule).toBeDefined();
    await page.getByRole("link", { name: FACTORY_CROSS_LINK_LABELS.toContentFactoryModule }).click();
    await expect(page).toHaveURL(/\/apps-tools\/content-factory\?section=micro-saas/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Content Factory" })).toBeVisible({ timeout: 30_000 });
  });

  test("execution lane tasks ↔ workflows ↔ jobs cross-links resolve", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/workflows", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Workflows" })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("link", { name: EXECUTION_LANE_CROSS_LINK_LABELS.toAsyncJobs }).click();
    await expect(page).toHaveURL(/\/jobs/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Async workflow jobs" })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("link", { name: EXECUTION_LANE_CROSS_LINK_LABELS.toTasksHub }).click();
    await expect(page).toHaveURL(/\/tasks/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Tasks" })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Table" }).click();

    const workflowsLink = EXECUTION_LANE_CROSS_LINKS.find((row) => row.from === "/tasks" && row.to === "/workflows");
    expect(workflowsLink).toBeDefined();
    await page.locator("main").getByRole("link", { name: EXECUTION_LANE_CROSS_LINK_LABELS.toWorkflows }).first().click();
    await expect(page).toHaveURL(/\/workflows/, { timeout: 45_000 });
  });

  test("agents lane foragers ↔ agents cross-links resolve", async ({ page }) => {
    test.skip(!OPERATOR_CONTROL_PLANE_ENABLED, "Requires operator control plane");

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/foragers", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Foragers" })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("link", { name: EXECUTION_LANE_CROSS_LINK_LABELS.toAgentsHub }).click();
    await expect(page).toHaveURL(/\/agents/, { timeout: 45_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Agents" })).toBeVisible({ timeout: 30_000 });

    const toForagers = AGENTS_LANE_CROSS_LINKS.find((row) => row.from === "/agents");
    expect(toForagers).toBeDefined();
    await page.locator("main").getByRole("link", { name: EXECUTION_LANE_CROSS_LINK_LABELS.toForagers }).click();
    await expect(page).toHaveURL(/\/foragers/, { timeout: 45_000 });
  });
});
