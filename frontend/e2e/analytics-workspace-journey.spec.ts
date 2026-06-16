import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

/**
 * Track L DA12 — end-to-end operator journey (mocked API):
 * question wizard → session dispatch → report → critic → lineage → export simulate.
 */
test.describe("Analytics workspace journey (DA12)", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await maybeInstallShellApiMocks(page);
    await seedDashboardSessionCookie(context, baseURL!);
    await suppressPwaInstallPrompt(page);
  });

  test("wizard through export simulate — full decision report lane", async ({ page }) => {
    const snapshotReady = page.waitForResponse(
      (res) => res.url().includes("analytics-workspace/snapshot") && res.status() === 200,
    );
    await page.goto("/apps-tools/analytics", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await snapshotReady;
    await expect(page.getByRole("heading", { name: "Analytics Workspace" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("analytics-workspace-overview")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("apps.analytics.decision_report.v1")).toBeVisible();

    // DA4 — Business question wizard → supervisor session
    const questionReady = page.waitForResponse(
      (res) =>
        res.url().includes("analytics-workspace/question-wizard") &&
        !res.url().includes("/preview") &&
        !res.url().includes("/submit") &&
        res.status() === 200,
    );
    await page.getByRole("button", { name: "Question" }).click();
    await questionReady;
    await expect(page.getByTestId("analytics-workspace-question")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-question-wizard")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("analytics-question-input").fill(
      "Why did organic signups drop 18% week over week in May?",
    );
    await expect(page.getByTestId("analytics-question-preview")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("analytics-question-submit").click();
    await expect(page.getByTestId("analytics-question-wizard")).toContainText("Analytics session started", {
      timeout: 10_000,
    });

    // DA5 + DA10 — Report artifact + critic closed loop
    await page.getByRole("button", { name: "Report" }).click();
    await expect(page.getByTestId("analytics-report-artifact")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Signup funnel review" })).toBeVisible();
    await expect(page.getByTestId("analytics-report-critic")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-report-critic-score")).toContainText("4.3/5");
    await page.getByTestId("analytics-report-critic-run").click();
    await expect(page.getByTestId("analytics-report-critic-result")).toContainText("Critic PASS", {
      timeout: 10_000,
    });

    // DA6 — Data lineage strip
    await page.getByRole("button", { name: "Lineage" }).click();
    await expect(page.getByTestId("analytics-data-lineage")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-lineage-row-kpi-wau")).toBeVisible();
    await expect(page.getByText("1 verified")).toBeVisible();

    // DA8 — Export inbox simulate submit (critic gate passed)
    await page.getByRole("button", { name: "Export inbox" }).click();
    await expect(page.getByTestId("analytics-export-lane")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("analytics-export-preview")).toBeVisible();
    await expect(page.getByText("critic 4.5/5")).toBeVisible();
    await page.getByTestId("analytics-export-submit").click();
    await expect(page.getByTestId("analytics-export-result")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Staged Notion page/)).toBeVisible();
  });
});
