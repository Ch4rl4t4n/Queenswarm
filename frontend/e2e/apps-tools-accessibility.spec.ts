import { expect, test } from "@playwright/test";
import {
  MCP_SNAPSHOT_FRESHNESS_AGING_MAX_MINUTES,
  MCP_SNAPSHOT_FRESHNESS_FRESH_MAX_MINUTES,
} from "@/lib/mcp-ops-observability";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const APPS_TOOLS_INDEX_STUB = {
  generated_at: new Date().toISOString(),
  version: "v1",
  workspaces: [
    {
      module_key: "marketing_automation",
      label: "Marketing Automation",
      layer: "apps_tools",
      summary: "Campaign publishing and distribution workflows.",
      status: "live",
      enabled: true,
      capability_keys: ["apps.marketing.publish_pipeline.v1"],
    },
  ],
  capabilities: [
    {
      capability_key: "apps.marketing.publish_pipeline.v1",
      label: "Marketing publish pipeline",
      owner_module: "marketing_automation",
      surface: "apps_tools",
      summary: "Generate and orchestrate multi-channel publish packs.",
      status: "live",
      version: "v1",
      risk_tier: "publish",
      requires_approval: true,
      input_schema_ref: "schemas/apps.marketing.publish_pipeline.input.v1.json",
      output_schema_ref: "schemas/apps.marketing.publish_pipeline.output.v1.json",
      enabled: true,
      sla_hint_sec: 180,
      dependency_keys: ["integrations.connector.invoke.v1"],
      tags: ["apps", "marketing", "publish"],
    },
  ],
  policies: [
    {
      module_key: "marketing_automation",
      label: "Marketing Automation",
      enabled: true,
      risk_tier: "publish",
      requires_approval: true,
      cooldown_sec: null,
      spend_cap_usd_24h: 10,
      time_limit_sec: 12,
      rate_limit_window_sec: 86400,
      rate_limit_max_global: 30,
      notes: ["Live publish is simulation-first."],
    },
  ],
};

const APPS_TOOLS_ANALYTICS_24H_STUB = {
  window: "24h",
  compact_mode: false,
  last_event_at: new Date().toISOString(),
  total_events: 4,
  counters: {
    "module_card_open:marketing_automation": 3,
    "module_details_open:marketing_automation": 1,
    "module_availability_hint_open:research_workspace": 2,
    "module_beta_hint_open:content_factory": 1,
    "mcp_ops_snapshot_retry:mcp_ops_studio": 3,
    "mcp_ops_retry_anomaly_ack:mcp_ops_studio": 1,
    "mcp_ops_retry_anomaly_resurfaced:mcp_ops_studio": 0,
    "mcp_ops_lifecycle_recommendation_open:mcp_ops_studio": 1,
    "mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio": 0,
  },
  module_funnel: [
    {
      module_key: "marketing_automation",
      card_open: 3,
      details_open: 1,
      section_quick_link: 1,
      dependency_jump: 0,
    },
    {
      module_key: "trading_automation",
      card_open: 2,
      details_open: 1,
      section_quick_link: 0,
      dependency_jump: 0,
    },
    {
      module_key: "browser_automation",
      card_open: 2,
      details_open: 0,
      section_quick_link: 0,
      dependency_jump: 0,
    },
    {
      module_key: "research_workspace",
      card_open: 1,
      details_open: 1,
      section_quick_link: 1,
      dependency_jump: 0,
    },
  ],
  top_movers: [
    {
      module_key: "marketing_automation",
      module_label: "Marketing Automation",
      current_score: 5,
      previous_score: 2,
      delta_score: 3,
    },
  ],
  recommendation: {
    module_key: "marketing_automation",
    module_label: "Marketing Automation",
    action: "review_details",
    reason: "High card opens but low details opens; validate governance and capability fit.",
  },
  recent_events: [
    {
      at: new Date(Date.now() - 60_000).toISOString(),
      event: "mcp_ops_snapshot_retry",
      module_key: "mcp_ops_studio",
      target_module_key: null,
      href: "/apps-tools/mcp-ops-studio?section=install",
      source: "mcp_ops_studio_retry",
    },
    {
      at: new Date().toISOString(),
      event: "module_card_open",
      module_key: "marketing_automation",
      target_module_key: null,
      href: "/apps-tools/marketing-automation",
      source: "module_card",
    },
  ],
};

const APPS_TOOLS_ANALYTICS_7D_STUB = {
  ...APPS_TOOLS_ANALYTICS_24H_STUB,
  window: "7d",
  total_events: 8,
  counters: {
    "module_card_open:marketing_automation": 5,
    "module_details_open:marketing_automation": 2,
    "module_availability_hint_open:research_workspace": 5,
    "module_beta_hint_open:content_factory": 3,
    "mcp_ops_snapshot_retry:mcp_ops_studio": 4,
    "mcp_ops_retry_anomaly_ack:mcp_ops_studio": 2,
    "mcp_ops_retry_anomaly_resurfaced:mcp_ops_studio": 1,
    "mcp_ops_lifecycle_recommendation_open:mcp_ops_studio": 2,
    "mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio": 1,
  },
  top_movers: [
    {
      module_key: "marketing_automation",
      module_label: "Marketing Automation",
      current_score: 8,
      previous_score: 6,
      delta_score: 2,
    },
  ],
};

const APPS_TOOLS_ANALYTICS_ALL_STUB = {
  ...APPS_TOOLS_ANALYTICS_24H_STUB,
  window: "all",
  total_events: 12,
  counters: {
    "module_card_open:marketing_automation": 7,
    "module_details_open:marketing_automation": 3,
    "module_availability_hint_open:research_workspace": 8,
    "module_beta_hint_open:content_factory": 6,
    "mcp_ops_snapshot_retry:mcp_ops_studio": 6,
    "mcp_ops_retry_anomaly_ack:mcp_ops_studio": 4,
    "mcp_ops_retry_anomaly_resurfaced:mcp_ops_studio": 2,
    "mcp_ops_lifecycle_recommendation_open:mcp_ops_studio": 3,
    "mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio": 2,
  },
  top_movers: [],
};

const MCP_OPS_SNAPSHOT_STUB = {
  generated_at: new Date().toISOString(),
  source: "read_only_mock",
  catalog: [
    { provider: "GitHub MCP", trust_tier: "verified", tool_count: 8, auth_mode: "oauth" },
    { provider: "Notion MCP", trust_tier: "community", tool_count: 5, auth_mode: "api_key" },
  ],
  install: [{ provider: "Linear MCP", requested_by: "operator", stage: "policy_review" }],
  health: [],
};

function mcpOpsSnapshotWithAgeMinutes(minutesAgo: number) {
  return {
    ...MCP_OPS_SNAPSHOT_STUB,
    generated_at: new Date(Date.now() - minutesAgo * 60_000).toISOString(),
  };
}

test.describe("Apps & Tools accessibility smoke", () => {
  test.beforeEach(async ({ page, context, baseURL }) => {
    await installShellApiMocks(page);
    await suppressPwaInstallPrompt(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    const analyticsPreferences = { window: "24h", compact_mode: false };
    await page.route("**/api/proxy/operator/apps-tools-index/analytics**", async (route) => {
      const requestUrl = new URL(route.request().url());
      const window = requestUrl.searchParams.get("window") ?? analyticsPreferences.window;
      const body =
        window === "7d"
          ? APPS_TOOLS_ANALYTICS_7D_STUB
          : window === "all"
            ? APPS_TOOLS_ANALYTICS_ALL_STUB
            : APPS_TOOLS_ANALYTICS_24H_STUB;
      const merged = { ...body, window, compact_mode: analyticsPreferences.compact_mode };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(merged),
      });
    });
    await page.route("**/api/proxy/operator/apps-tools-index/analytics/preferences**", async (route) => {
      const patch = (route.request().postDataJSON() ?? {}) as {
        window?: "24h" | "7d" | "all";
        compact_mode?: boolean;
      };
      if (patch.window) {
        analyticsPreferences.window = patch.window;
      }
      if (typeof patch.compact_mode === "boolean") {
        analyticsPreferences.compact_mode = patch.compact_mode;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, ...analyticsPreferences }),
      });
    });
    await page.route("**/api/proxy/operator/apps-tools-index", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(APPS_TOOLS_INDEX_STUB),
      });
    });
    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MCP_OPS_SNAPSHOT_STUB),
      });
    });
  });

  test("module details overlay closes on Escape and restores focus", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const trigger = page.getByRole("button", { name: "Module details" }).first();
    await expect(trigger).toBeVisible({ timeout: 20_000 });
    await trigger.click();

    const dialogHeading = page.getByRole("heading", { name: "Marketing Automation module details" });
    await expect(dialogHeading).toBeVisible({ timeout: 10_000 });

    await page.keyboard.press("Escape");
    await expect(dialogHeading).toBeHidden({ timeout: 10_000 });
    await expect(trigger).toBeFocused();
  });

  test("stub module card shows disabled action with inline availability feedback", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const stubCard = page
      .getByRole("heading", { name: "Research Workspace" })
      .locator("xpath=ancestor::article[1]");
    await expect(stubCard).toBeVisible({ timeout: 20_000 });
    const unavailableButton = stubCard.getByRole("button", { name: "Module unavailable" });
    await expect(unavailableButton).toBeVisible({ timeout: 10_000 });
    await expect(unavailableButton).toBeDisabled();
    await expect(
      stubCard.getByText(
        "This module is not available yet. Capability contract is visible, but execution is disabled.",
      ),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("keyboard tab order stays stable with disabled CTA and availability hint controls", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const contentFactoryOpen = page
      .getByRole("heading", { name: "Content Factory" })
      .locator("xpath=ancestor::article[1]")
      .getByRole("link", { name: "Open module" });
    const contentFactoryBetaHint = page
      .getByRole("heading", { name: "Content Factory" })
      .locator("xpath=ancestor::article[1]")
      .getByText("Beta readiness hint");
    await expect(contentFactoryOpen).toBeVisible({ timeout: 10_000 });
    await expect(contentFactoryBetaHint).toBeVisible({ timeout: 10_000 });
    const researchCard = page
      .getByRole("heading", { name: "Research Workspace" })
      .locator("xpath=ancestor::article[1]");
    const researchHintTrigger = researchCard.getByText("Availability hint");
    await expect(researchHintTrigger).toBeVisible({ timeout: 10_000 });
    await researchHintTrigger.focus();
    await expect(researchHintTrigger).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(contentFactoryBetaHint).toBeFocused();

    const unavailableButton = researchCard.getByRole("button", { name: "Module unavailable" });
    await expect(unavailableButton).toBeDisabled();
    await expect(unavailableButton).not.toBeFocused();
  });

  test("keyboard hint disclosure emits read-only telemetry events", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const betaCard = page.getByRole("heading", { name: "Content Factory" }).locator("xpath=ancestor::article[1]");
    const betaHint = betaCard.getByText("Beta readiness hint");
    await expect(betaHint).toBeVisible({ timeout: 10_000 });
    await betaHint.focus();
    await page.keyboard.press(" ");
    await expect(betaCard.locator("details").first()).toHaveAttribute("open", "");

    const unavailableCard = page
      .getByRole("heading", { name: "Research Workspace" })
      .locator("xpath=ancestor::article[1]");
    const availabilityHint = unavailableCard.getByText("Availability hint");
    await expect(availabilityHint).toBeVisible({ timeout: 10_000 });
    await availabilityHint.focus();
    await page.keyboard.press("Enter");
    await expect(unavailableCard.locator("details").first()).toHaveAttribute("open", "");

    await expect.poll(() => capturedEvents.length).toBe(2);
    const events = capturedEvents.map((row) => row.event);
    expect(events).toContain("module_beta_hint_open");
    expect(events).toContain("module_availability_hint_open");
  });

  test("reduced motion deep-link renders target section", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/apps-tools/research-workspace?section=hivemind#hivemind-links", {
      waitUntil: "load",
      timeout: 60_000,
    });

    const section = page.locator("#hivemind-links");
    await expect(section).toBeVisible({ timeout: 20_000 });
  });

  test("mcp ops studio deep-link renders target section", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/apps-tools/mcp-ops-studio?section=health#mcp-health", {
      waitUntil: "load",
      timeout: 60_000,
    });

    const section = page.locator("#mcp-health");
    await expect(section).toBeVisible({ timeout: 20_000 });
  });

  test("mcp ops studio supports keyboard section switching and card actions", async ({ page }) => {
    await page.goto("/apps-tools/mcp-ops-studio?section=catalog#mcp-catalog", {
      waitUntil: "load",
      timeout: 60_000,
    });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools/mcp-ops-studio?section=catalog");
      return;
    }

    const installTab = page.getByRole("button", { name: "Install queue" });
    await expect(installTab).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Snapshot source: read_only_mock")).toBeVisible({ timeout: 10_000 });
    await installTab.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#mcp-install")).toBeVisible({ timeout: 10_000 });

    const installAction = page.getByRole("button", { name: "Queue governed install" });
    await installAction.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Install request queued in read-only preview mode.")).toBeVisible({ timeout: 10_000 });

    const healthTab = page.getByRole("button", { name: "Health checks" });
    await healthTab.focus();
    await page.keyboard.press(" ");
    await expect(page.locator("#mcp-health")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("No health probes yet for this window.")).toBeVisible({ timeout: 10_000 });

    const healthAction = page.getByRole("button", { name: "Run health probe" });
    await healthAction.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Health probe scheduled in read-only preview mode.")).toBeVisible({ timeout: 10_000 });
  });

  test("mcp ops studio shows error fallback when backend snapshot fails", async ({ page }) => {
    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "snapshot_error" }),
      });
    });

    await page.goto("/apps-tools/mcp-ops-studio?section=catalog#mcp-catalog", {
      waitUntil: "load",
      timeout: 60_000,
    });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools/mcp-ops-studio?section=catalog");
      return;
    }

    await expect(page.getByText("MCP Ops section unavailable")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: "Retry section load" })).toBeVisible({ timeout: 10_000 });
  });

  test("mcp ops retry recovers from transient backend 5xx and keeps section stable", async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      attempts += 1;
      if (attempts <= 3) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "temporary_outage" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MCP_OPS_SNAPSHOT_STUB),
      });
    });

    await page.goto("/apps-tools/mcp-ops-studio?section=install#mcp-install", {
      waitUntil: "load",
      timeout: 60_000,
    });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools/mcp-ops-studio?section=install");
      return;
    }

    await expect(page.getByText("MCP Ops section unavailable")).toBeVisible({ timeout: 20_000 });
    const retry = page.getByRole("button", { name: "Retry section load" });
    await retry.focus();
    await expect(retry).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.locator("#mcp-install")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("button", { name: "Install queue" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("button", { name: "Queue governed install" })).toBeVisible({ timeout: 10_000 });
  });

  test("mcp ops snapshot freshness chip reflects fresh/aging/stale thresholds", async ({ page }) => {
    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mcpOpsSnapshotWithAgeMinutes(Math.max(0, MCP_SNAPSHOT_FRESHNESS_FRESH_MAX_MINUTES - 1))),
      });
    });
    await page.goto("/apps-tools/mcp-ops-studio?section=catalog#mcp-catalog", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") return;
    await expect(page.getByText("Fresh snapshot")).toBeVisible({ timeout: 10_000 });

    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mcpOpsSnapshotWithAgeMinutes(MCP_SNAPSHOT_FRESHNESS_FRESH_MAX_MINUTES + 1)),
      });
    });
    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("Aging snapshot")).toBeVisible({ timeout: 10_000 });

    await page.route("**/api/proxy/operator/apps-tools/mcp-ops-studio/snapshot", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mcpOpsSnapshotWithAgeMinutes(MCP_SNAPSHOT_FRESHNESS_AGING_MAX_MINUTES + 1)),
      });
    });
    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("Stale snapshot")).toBeVisible({ timeout: 10_000 });
  });

  test("analytics widget toggles windows and shows recommendation", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByRole("heading", { name: "Module usage pulse" })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("Recommended next action")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Marketing Automation: +3 (2 → 5)")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Marketing Automation: +2 (6 → 8)")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "compact" }).click();
    await expect(page.getByText("Top movers")).toBeHidden({ timeout: 10_000 });
  });

  test("lifecycle-aware recommendation action switches across windows and tracks engagement", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const recommendationAction = page.getByRole("link", { name: "Open MCP health checks" }).first();
    await expect(recommendationAction).toBeVisible({ timeout: 10_000 });
    await recommendationAction.focus();
    await expect(recommendationAction).toBeFocused();
    await page.keyboard.press("Enter");
    await expect
      .poll(() => capturedEvents.some((row) => row.event === "mcp_ops_lifecycle_recommendation_open"))
      .toBeTruthy();

    const acknowledge = page.getByRole("button", { name: "Acknowledge anomaly" });
    await acknowledge.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("link", { name: "Monitor retry trend" })).toBeVisible({ timeout: 10_000 });

    const chip7d = page.getByRole("button", { name: "7d" });
    await chip7d.focus();
    await expect(chip7d).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("link", { name: "Open MCP health checks" })).toBeVisible({ timeout: 10_000 });
  });

  test("recommendation cooldown hint persists across reload and compact keyboard toggles", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const recommendationAction = page.getByRole("link", { name: "Open MCP health checks" }).first();
    await expect(page.getByText(/Recommendation opens/)).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText(/Recommendation opens .*24h 1 .*7d 2 .*all 3 .*Force opens .*24h 0 .*7d 1 .*all 2/),
    ).toBeVisible({ timeout: 10_000 });
    await recommendationAction.focus();
    await expect(recommendationAction).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByText("last opened")).toBeVisible({ timeout: 10_000 });

    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.focus();
    await page.keyboard.press("Enter");
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("last opened")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("last opened")).toBeVisible({ timeout: 10_000 });

    const chip7d = page.getByRole("button", { name: "7d" });
    await chip7d.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("last opened")).toBeVisible({ timeout: 10_000 });
  });

  test("recommendation cooldown guard blocks immediate retry and recovers after threshold", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const recommendationAction = page.getByRole("link", { name: "Open MCP health checks" }).first();
    await recommendationAction.focus();
    await page.keyboard.press("Enter");
    await expect
      .poll(
        () => capturedEvents.filter((row) => row.event === "mcp_ops_lifecycle_recommendation_open").length,
      )
      .toBeGreaterThan(0);

    await recommendationAction.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/Retry in \d+m/)).toBeVisible({ timeout: 10_000 });
    await expect
      .poll(() => capturedEvents.some((row) => row.event === "mcp_ops_lifecycle_recommendation_cooldown_block"))
      .toBeTruthy();

    await page.evaluate(() => {
      window.localStorage.setItem(
        "apps-tools:mcp-lifecycle-recommendation-at:v1",
        new Date(Date.now() - 10 * 60_000).toISOString(),
      );
    });
    await page.reload({ waitUntil: "load" });
    await expect(page.getByText(/Retry in \d+m/)).toHaveCount(0);

    const recommendationActionAfterCooldown = page.getByRole("link", { name: "Open MCP health checks" }).first();
    await recommendationActionAfterCooldown.focus();
    await page.keyboard.press("Enter");
    await expect
      .poll(
        () => capturedEvents.filter((row) => row.event === "mcp_ops_lifecycle_recommendation_open").length,
      )
      .toBeGreaterThan(1);
  });

  test("cooldown guard supports confirmed force-open override and tracks telemetry", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const recommendationAction = page.getByRole("link", { name: "Open MCP health checks" }).first();
    await recommendationAction.focus();
    await page.keyboard.press("Enter");
    await recommendationAction.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/Retry in \d+m/)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Force open once" })).toBeVisible({ timeout: 10_000 });

    const forceOpenOnce = page.getByRole("button", { name: "Force open once" });
    await forceOpenOnce.focus();
    await expect(forceOpenOnce).toBeFocused();
    await page.keyboard.press("Enter");

    const confirmForceOpen = page.getByRole("button", { name: "Confirm force open" });
    await expect(confirmForceOpen).toBeVisible({ timeout: 10_000 });
    await confirmForceOpen.focus();
    await expect(confirmForceOpen).toBeFocused();
    await page.keyboard.press("Enter");

    await expect
      .poll(() => capturedEvents.some((row) => row.event === "mcp_ops_lifecycle_recommendation_cooldown_override"))
      .toBeTruthy();
    await expect
      .poll(() => capturedEvents.filter((row) => row.event === "mcp_ops_lifecycle_recommendation_open").length)
      .toBeGreaterThan(1);
  });

  test("analytics widget shows hint interaction strip with movers and recommendation", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByText("UX hint interactions")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("availability 2")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("beta 1")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Top movers")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Recommended next action")).toBeVisible({ timeout: 10_000 });
  });

  test("hint trend cue updates across windows and keeps compact toggle behavior", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByText("Hint trend watch (24h)")).toBeVisible({ timeout: 10_000 });
    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByText("Hint trend hot (7d)")).toBeVisible({ timeout: 10_000 });
    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByText("Hint trend watch (all)")).toBeVisible({ timeout: 10_000 });

    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.click();
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("Top movers")).toBeHidden({ timeout: 10_000 });
  });

  test("analytics widget shows MCP retry rollup and keeps it readable in compact mode", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByText("MCP snapshot retries 3")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("last retry")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Retry spike detected in 24h")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Retry trend")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("24h 3")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("7d 4")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("all 6")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Retry anomaly")).toBeVisible({ timeout: 10_000 });
    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.focus();
    await page.keyboard.press("Enter");
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("MCP snapshot retries 3")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("24h 3")).toBeVisible({ timeout: 10_000 });
  });

  test("retry anomaly acknowledgement persists across reload and supports keyboard", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByText("Retry anomaly")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Clear acknowledgment" })).toHaveCount(0);
    const scopeWindow = page.getByRole("button", { name: "this window" });
    await expect(scopeWindow).toBeVisible({ timeout: 10_000 });
    const acknowledge = page.getByRole("button", { name: "Acknowledge anomaly" });
    await acknowledge.focus();
    await expect(acknowledge).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Anomaly acknowledged")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("acked")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Acknowledge anomaly" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Clear acknowledgment" })).toBeVisible({ timeout: 10_000 });
    await expect.poll(() => capturedEvents.some((row) => row.event === "mcp_ops_retry_anomaly_ack")).toBeTruthy();

    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("Anomaly acknowledged")).toBeVisible({ timeout: 10_000 });
    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.focus();
    await page.keyboard.press("Enter");
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("Anomaly acknowledged")).toBeVisible({ timeout: 10_000 });
    const clearAck = page.getByRole("button", { name: "Clear acknowledgment" });
    await clearAck.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Acknowledge anomaly" })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Retry anomaly")).toBeVisible({ timeout: 10_000 });
  });

  test("retry anomaly resurfaces when trend worsens and emits telemetry", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    let retry24 = 3;
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });
    await page.route("**/api/proxy/operator/apps-tools-index/analytics**", async (route) => {
      const requestUrl = new URL(route.request().url());
      const window = requestUrl.searchParams.get("window") ?? "24h";
      const body =
        window === "7d"
          ? {
              ...APPS_TOOLS_ANALYTICS_7D_STUB,
              counters: {
                ...APPS_TOOLS_ANALYTICS_7D_STUB.counters,
                "mcp_ops_snapshot_retry:mcp_ops_studio": 4,
              },
            }
          : window === "all"
            ? {
                ...APPS_TOOLS_ANALYTICS_ALL_STUB,
                counters: {
                  ...APPS_TOOLS_ANALYTICS_ALL_STUB.counters,
                  "mcp_ops_snapshot_retry:mcp_ops_studio": 6,
                },
              }
            : {
                ...APPS_TOOLS_ANALYTICS_24H_STUB,
                counters: {
                  ...APPS_TOOLS_ANALYTICS_24H_STUB.counters,
                  "mcp_ops_snapshot_retry:mcp_ops_studio": retry24,
                },
              };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...body, window }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const acknowledge = page.getByRole("button", { name: "Acknowledge anomaly" });
    await acknowledge.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Anomaly acknowledged")).toBeVisible({ timeout: 10_000 });

    retry24 = 5;
    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("Retry anomaly")).toBeVisible({ timeout: 10_000 });
    await expect.poll(() => capturedEvents.some((row) => row.event === "mcp_ops_retry_anomaly_resurfaced")).toBeTruthy();
  });

  test("module card quick reset works in compact mode and keeps keyboard order stable", async ({ page }) => {
    const capturedEvents: Array<{ event?: string; source?: string; module_key?: string }> = [];
    let retry24 = 3;
    await page.route("**/api/proxy/operator/apps-tools-index/analytics**", async (route) => {
      const requestUrl = new URL(route.request().url());
      const window = requestUrl.searchParams.get("window") ?? "24h";
      const body =
        window === "7d"
          ? {
              ...APPS_TOOLS_ANALYTICS_7D_STUB,
              counters: {
                ...APPS_TOOLS_ANALYTICS_7D_STUB.counters,
                "mcp_ops_snapshot_retry:mcp_ops_studio": 4,
              },
            }
          : window === "all"
            ? {
                ...APPS_TOOLS_ANALYTICS_ALL_STUB,
                counters: {
                  ...APPS_TOOLS_ANALYTICS_ALL_STUB.counters,
                  "mcp_ops_snapshot_retry:mcp_ops_studio": 6,
                },
              }
            : {
                ...APPS_TOOLS_ANALYTICS_24H_STUB,
                counters: {
                  ...APPS_TOOLS_ANALYTICS_24H_STUB.counters,
                  "mcp_ops_snapshot_retry:mcp_ops_studio": retry24,
                },
              };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...body, window }),
      });
    });
    await page.route("**/api/proxy/operator/apps-tools-index/events", async (route) => {
      const payload = (route.request().postDataJSON() ?? {}) as {
        event?: string;
        source?: string;
        module_key?: string;
      };
      capturedEvents.push(payload);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, stored_events: capturedEvents.length }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await expect(page.getByText("Lifecycle active")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Ack vs resurfaced")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("24h 1/0", { exact: true }).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("7d 2/1", { exact: true }).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("all 4/2", { exact: true }).first()).toBeVisible({ timeout: 10_000 });

    const acknowledge = page.getByRole("button", { name: "Acknowledge anomaly" });
    await acknowledge.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Anomaly acknowledged")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Lifecycle suppressed")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("scope this window")).toBeVisible({ timeout: 10_000 });

    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.focus();
    await page.keyboard.press("Enter");
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");

    const quickReset = page.getByRole("button", { name: "Reset anomaly ack" });
    await expect(quickReset).toBeVisible({ timeout: 10_000 });
    await quickReset.focus();
    await expect(quickReset).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(quickReset).not.toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(quickReset).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Retry anomaly")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Lifecycle active")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Acknowledge anomaly" })).toBeVisible({ timeout: 10_000 });
    await expect
      .poll(() => capturedEvents.some((row) => row.event === "mcp_ops_retry_anomaly_ack_reset"))
      .toBeTruthy();

    const acknowledgeAgain = page.getByRole("button", { name: "Acknowledge anomaly" });
    await acknowledgeAgain.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Lifecycle suppressed")).toBeVisible({ timeout: 10_000 });

    retry24 = 5;
    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("Lifecycle resurfaced")).toBeVisible({ timeout: 10_000 });
    await expect
      .poll(() => capturedEvents.some((row) => row.event === "mcp_ops_retry_anomaly_resurfaced"))
      .toBeTruthy();
  });

  test("mcp ops module details exposes retry anomaly action hint", async ({ page }) => {
    await page.route("**/api/proxy/operator/apps-tools-index", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...APPS_TOOLS_INDEX_STUB,
          workspaces: [
            ...APPS_TOOLS_INDEX_STUB.workspaces,
            {
              module_key: "mcp_ops_studio",
              label: "MCP Ops Studio",
              layer: "apps_tools",
              summary: "Catalog-first MCP provider operations lane.",
              status: "beta",
              enabled: true,
              capability_keys: ["apps.mcp.catalog.healthcheck.v1"],
            },
          ],
          capabilities: [
            ...APPS_TOOLS_INDEX_STUB.capabilities,
            {
              capability_key: "apps.mcp.catalog.healthcheck.v1",
              label: "MCP health diagnostics",
              owner_module: "mcp_ops_studio",
              surface: "apps_tools",
              summary: "Read-only MCP connector and tool health probes.",
              status: "beta",
              version: "v1",
              risk_tier: "read",
              requires_approval: false,
              input_schema_ref: "schemas/apps.mcp.catalog.healthcheck.input.v1.json",
              output_schema_ref: "schemas/apps.mcp.catalog.healthcheck.output.v1.json",
              enabled: true,
              sla_hint_sec: 45,
              dependency_keys: [],
              tags: ["apps", "mcp", "health"],
            },
          ],
          policies: [
            ...APPS_TOOLS_INDEX_STUB.policies,
            {
              module_key: "mcp_ops_studio",
              label: "MCP Ops Studio",
              enabled: true,
              risk_tier: "read",
              requires_approval: false,
              cooldown_sec: null,
              spend_cap_usd_24h: null,
              time_limit_sec: 10,
              rate_limit_window_sec: 86400,
              rate_limit_max_global: 100,
              notes: ["Read-only MCP observability lane."],
            },
          ],
        }),
      });
    });

    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const mcpCard = page.getByRole("heading", { name: "MCP Ops Studio" }).locator("xpath=ancestor::article[1]");
    const detailsButton = mcpCard.getByRole("button", { name: "Module details" });
    await expect(detailsButton).toBeVisible({ timeout: 20_000 });
    await detailsButton.click();

    await expect(page.getByText("Sustained retry anomaly detected.")).toBeVisible({ timeout: 10_000 });
    const detailsDialog = page.getByLabel("MCP Ops Studio module details");
    await expect(detailsDialog.getByRole("link", { name: "Open MCP health checks" })).toBeVisible({ timeout: 10_000 });
  });

  test("compact toggle supports keyboard and keeps focus", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const compactToggle = page.getByRole("button", { name: "compact" });
    await expect(compactToggle).toBeVisible({ timeout: 20_000 });
    await compactToggle.focus();
    await expect(compactToggle).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");
    await expect(compactToggle).toBeFocused();
  });

  test("tablet compact mode reduces analytics card density", async ({ page }) => {
    await page.setViewportSize({ width: 900, height: 1200 });
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const widget = page.getByRole("heading", { name: "Module usage pulse" }).locator("xpath=ancestor::section[1]");
    await expect(widget).toBeVisible({ timeout: 20_000 });
    await expect(widget.locator("article")).toHaveCount(4);

    const compactToggle = page.getByRole("button", { name: "compact" });
    await compactToggle.click();
    await expect(widget.locator("article")).toHaveCount(2);
  });

  test("compact mode preference survives page reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const compactToggle = page.getByRole("button", { name: "compact" });
    await expect(compactToggle).toHaveAttribute("aria-pressed", "false");
    await compactToggle.click();
    await expect(compactToggle).toHaveAttribute("aria-pressed", "true");

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "compact" })).toHaveAttribute("aria-pressed", "true");
  });

  test("window preference survives page reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
  });

  test("window and compact preferences restore together after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "7d" }).click();
    await page.getByRole("button", { name: "compact" }).click();
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "compact" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");

    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "compact" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("Top movers")).toBeHidden({ timeout: 10_000 });
  });

  test("all window preference survives reload with active chip", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");

    await page.reload({ waitUntil: "load" });
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
  });

  test("24h window chip reactivates after all and survives reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "24h" }).click();
    await expect(page.getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });
  });

  test("all window and compact mode restore together after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "all" }).click();
    await page.getByRole("button", { name: "compact" }).click();
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "compact" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Top movers")).toBeHidden({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("button", { name: "compact" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Top movers")).toBeHidden({ timeout: 10_000 });
  });

  test("all to 7d to all keeps active chip and counter after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
  });

  test("7d chip stays active after keyboard retoggle and reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "all" }).click();
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");

    const sevenDayChip = page.getByRole("button", { name: "7d" });
    await sevenDayChip.focus();
    await expect(sevenDayChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(sevenDayChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
  });

  test("24h chip keyboard-selects after 7d and persists after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    const twentyFourHourChip = page.getByRole("button", { name: "24h" });
    await twentyFourHourChip.focus();
    await expect(twentyFourHourChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(twentyFourHourChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });
  });

  test("all chip keyboard-selects after 24h and persists after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    await page.getByRole("button", { name: "24h" }).click();
    await expect(page.getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });

    const allChip = page.getByRole("button", { name: "all" });
    await allChip.focus();
    await expect(allChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(allChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
  });

  test("all chip stays active after keyboard re-activation and persists after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const allChip = page.getByRole("button", { name: "all" });
    await allChip.click();
    await expect(allChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await allChip.focus();
    await expect(allChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(allChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "all" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("12 events")).toBeVisible({ timeout: 10_000 });
  });

  test("7d chip stays active after keyboard re-activation and persists after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const sevenDayChip = page.getByRole("button", { name: "7d" });
    await sevenDayChip.click();
    await expect(sevenDayChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    await sevenDayChip.focus();
    await expect(sevenDayChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(sevenDayChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("8 events")).toBeVisible({ timeout: 10_000 });
  });

  test("24h chip stays active after keyboard re-activation and persists after reload", async ({ page }) => {
    await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
    if (new URL(page.url()).pathname === "/login") {
      expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
      return;
    }

    const twentyFourHourChip = page.getByRole("button", { name: "24h" });
    await twentyFourHourChip.click();
    await expect(twentyFourHourChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });

    await twentyFourHourChip.focus();
    await expect(twentyFourHourChip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(twentyFourHourChip).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });

    await page.reload({ waitUntil: "load" });
    await expect(page.getByRole("button", { name: "24h" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByText("4 events")).toBeVisible({ timeout: 10_000 });
  });

  const preselectedKeyboardScenarios: ReadonlyArray<{
    chip: "24h" | "7d" | "all";
    eventsLabel: string;
    keyPress: "Enter" | " ";
    label: string;
  }> = [
    { chip: "all", eventsLabel: "12 events", keyPress: "Enter", label: "enter all" },
    { chip: "7d", eventsLabel: "8 events", keyPress: "Enter", label: "enter 7d" },
    { chip: "24h", eventsLabel: "4 events", keyPress: "Enter", label: "enter 24h" },
    { chip: "all", eventsLabel: "12 events", keyPress: " ", label: "space all" },
  ];

  for (const scenario of preselectedKeyboardScenarios) {
    test(`preselected ${scenario.chip} chip stays active after keyboard ${scenario.label} re-activation and persists after reload`, async ({
      page,
    }) => {
      await page.goto("/apps-tools", { waitUntil: "load", timeout: 60_000 });
      if (new URL(page.url()).pathname === "/login") {
        expect(new URL(page.url()).searchParams.get("next")).toBe("/apps-tools");
        return;
      }

      const chip = page.getByRole("button", { name: scenario.chip });
      await chip.click();
      await expect(chip).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByText(scenario.eventsLabel)).toBeVisible({ timeout: 10_000 });

      await page.reload({ waitUntil: "load" });
      const preselectedChip = page.getByRole("button", { name: scenario.chip });
      await expect(preselectedChip).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByText(scenario.eventsLabel)).toBeVisible({ timeout: 10_000 });

      await preselectedChip.focus();
      await expect(preselectedChip).toBeFocused();
      await page.keyboard.press(scenario.keyPress);
      await expect(preselectedChip).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByText(scenario.eventsLabel)).toBeVisible({ timeout: 10_000 });

      await page.reload({ waitUntil: "load" });
      await expect(page.getByRole("button", { name: scenario.chip })).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByText(scenario.eventsLabel)).toBeVisible({ timeout: 10_000 });
    });
  }
});
