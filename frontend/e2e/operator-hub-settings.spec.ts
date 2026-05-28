import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const operatorHubE2eEnabled = process.env.E2E_OPERATOR_HUB === "1";

const OPERATOR_HUB_SNAPSHOT = {
  enabled: true,
  generated_at: new Date().toISOString(),
  modules: [
    { id: "agent_os", label: "Agent OS P8", enabled: true, env_hint: null },
    { id: "publish_performance", label: "Publish Performance", enabled: true, env_hint: null },
    { id: "live_lane", label: "Live Lane Prep", enabled: true, env_hint: null },
  ],
  env_flags: [
    {
      key: "SOCIAL_PUBLISH_LIVE_ENABLED",
      active: false,
      description: "Social API live posts (default off).",
    },
    {
      key: "PREDICTION_MARKETS_LIVE_TRADING_ENABLED",
      active: false,
      description: "Polymarket real-money orders (default off).",
    },
  ],
  live_lane: {
    enabled: true,
    generated_at: new Date().toISOString(),
    progress_pct: 14,
    trading_live_flag: false,
    publish_live_flag: false,
    steps: [
      { id: "oauth_env", lane: "publish", label: "OAuth vendor keys", status: "pending" },
      { id: "simulate", lane: "publish", label: "Simulate approved packs", status: "done" },
    ],
    actions: [{ id: "studio", label: "Execution Studio", href: "/integrations?tab=studio" }],
  },
  publish_onboarding: {
    generated_at: new Date().toISOString(),
    progress_pct: 36,
    steps: [
      {
        id: "oauth_env",
        label: "Add OAuth vendor keys",
        status: "ready",
        detail: "Fill .env.prod.oauth",
        link: null,
      },
      {
        id: "connect",
        label: "Connect social connector",
        status: "blocked",
        detail: "Requires OAuth keys",
        link: "/integrations?tab=studio",
      },
    ],
    flags: { live_enabled: false, simulate_ok: true },
  },
  social_oauth: {
    enabled: true,
    generated_at: new Date().toISOString(),
    live_publish_enabled: false,
    env_configured_count: 0,
    active_channel_count: 0,
    ready_items_count: 2,
    simulate_count: 2,
    channels: [
      {
        channel: "instagram",
        label: "Instagram",
        env_configured: false,
        installed: false,
        active: false,
        credentials_ok: false,
        env_id_key: "OAUTH_META_CLIENT_ID",
        env_secret_key: "OAUTH_META_CLIENT_SECRET",
        console_url: "https://developers.facebook.com/apps/",
      },
      {
        channel: "twitter",
        label: "X (Twitter)",
        env_configured: false,
        installed: false,
        active: false,
        credentials_ok: false,
        env_id_key: "OAUTH_X_CLIENT_ID",
        env_secret_key: "OAUTH_X_CLIENT_SECRET",
        console_url: "https://developer.x.com/en/portal/dashboard",
      },
    ],
    blockers: [
      "No OAuth vendor keys in server env — fill .env.prod.oauth and redeploy.",
      "SOCIAL_PUBLISH_LIVE_ENABLED=false — simulate OK; live blocked until operator enables.",
    ],
    prep_scripts: { all: "./scripts/operator-social-oauth-prep-all.sh" },
  },
  next_action: {
    priority: 1,
    title: "Add OAuth vendor keys",
    why: "Social publish needs at least one vendor OAuth app before Connect.",
    doc: "docs/OPERATOR_FIRST_LIVE_POST.md",
    commands: ["./scripts/operator-social-oauth-prep-all.sh"],
    ui_link: "/settings/harness#operator-hub",
    step_id: "oauth_env",
  },
  docs: { first_live_post: "docs/OPERATOR_FIRST_LIVE_POST.md" },
};

const TRUSTED_AUTO_POLICY = {
  global_enabled: false,
  tenant_enabled: false,
  min_simulates_required: 5,
  live_enabled: false,
  channels: [
    {
      channel: "instagram",
      mode: "manual",
      successful_simulates: 2,
      min_simulates_required: 5,
      auto_eligible: false,
    },
  ],
};

const PREFLIGHT_RESPONSE = {
  trading: { allowed: false, blockers: ["PREDICTION_MARKETS_LIVE_TRADING_ENABLED=false"] },
  publish: { allowed: false, blockers: ["SOCIAL_PUBLISH_LIVE_ENABLED=false", "No OAuth keys configured"] },
};

test.describe("Operator hub settings", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test.beforeEach(() => {
    test.skip(!operatorHubE2eEnabled, "Set E2E_OPERATOR_HUB=1 to run operator hub settings checks.");
  });

  test.beforeEach(async ({ context, baseURL, page }) => {
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);

    await page.route("**/api/proxy/settings/operator-hub/preflight", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(PREFLIGHT_RESPONSE),
      });
    });

    await page.route("**/api/proxy/settings/operator-hub", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(OPERATOR_HUB_SNAPSHOT),
      });
    });

    await page.route("**/api/proxy/social-publish/trusted-auto", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(TRUSTED_AUTO_POLICY),
      });
    });
  });

  test("harness settings shows operator hub next action, OAuth console links, and preflight", async ({ page }) => {
    await page.goto("/settings/harness", { waitUntil: "domcontentloaded", timeout: 60_000 });

    const hub = page.locator("#operator-hub");
    await expect(hub).toBeVisible({ timeout: 45_000 });
    await expect(hub.getByRole("heading", { name: /Autonomy & live lane hub/i })).toBeVisible();
    await expect(hub.getByText("Next action")).toBeVisible();
    await expect(hub.getByRole("heading", { name: "Add OAuth vendor keys" })).toBeVisible();
    const advancedToggle = hub.getByRole("button", { name: /Advanced lane & OAuth/i });
    if ((await advancedToggle.getAttribute("aria-expanded")) !== "true") {
      await advancedToggle.click();
    }
    await expect(advancedToggle).toHaveAttribute("aria-expanded", "true");
    const controlsId = await advancedToggle.getAttribute("aria-controls");
    expect(controlsId).toBeTruthy();
    await expect(page.locator(`#${controlsId}`)).toHaveAttribute("role", "region");
    await expect(hub.getByText("Publish lane onboarding 36%")).toBeVisible();
    await expect(hub.getByText("Social OAuth readiness")).toBeVisible();
    await expect(hub.getByText("Env keys: 0/4")).toBeVisible();
    await expect(hub.getByRole("link", { name: "Console" }).first()).toHaveAttribute(
      "href",
      "https://developers.facebook.com/apps/",
    );
    await expect(hub.getByText("OAUTH_META_CLIENT_ID + OAUTH_META_CLIENT_SECRET")).toBeVisible();
    await expect(hub.getByText("Trusted auto-publish")).toBeVisible();

    await hub.getByRole("button", { name: "Preflight dry-run" }).click();
    const preflightPanel = hub.locator("div.rounded.border").filter({ hasText: "Trading:" });
    await expect(preflightPanel).toBeVisible();
    await expect(preflightPanel.getByText("Publish:")).toBeVisible();
    await expect(preflightPanel.getByText("PREDICTION_MARKETS_LIVE_TRADING_ENABLED=false")).toBeVisible();
    await expect(preflightPanel.getByText("SOCIAL_PUBLISH_LIVE_ENABLED=false")).toBeVisible();
  });

  test("trusted auto enable saves tenant policy when live flags on", async ({ page }) => {
    let policy = {
      global_enabled: true,
      tenant_enabled: false,
      min_simulates_required: 5,
      live_enabled: true,
      channels: [
        {
          channel: "instagram",
          mode: "manual" as const,
          successful_simulates: 6,
          min_simulates_required: 5,
          auto_eligible: true,
        },
      ],
    };

    await page.unroute("**/api/proxy/social-publish/trusted-auto");
    await page.route("**/api/proxy/social-publish/trusted-auto", async (route) => {
      if (route.request().method() === "PATCH") {
        const body = route.request().postDataJSON() as { enabled?: boolean };
        if (typeof body.enabled === "boolean") {
          policy = { ...policy, tenant_enabled: body.enabled };
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(policy),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(policy),
      });
    });

    await page.goto("/settings/harness", { waitUntil: "domcontentloaded", timeout: 60_000 });
    const hub = page.locator("#operator-hub");
    const advancedToggle = hub.getByRole("button", { name: /Advanced lane & OAuth/i });
    if ((await advancedToggle.getAttribute("aria-expanded")) !== "true") {
      await advancedToggle.click();
    }
    await expect(hub.getByText("Trusted auto-publish")).toBeVisible({ timeout: 45_000 });
    await expect(hub.getByRole("button", { name: "Enable auto" })).toBeEnabled();
    await hub.getByRole("button", { name: "Enable auto" }).click();
    await expect(hub.getByRole("button", { name: "Auto on" })).toBeVisible();
    await expect(page.getByText("Trusted auto policy saved.")).toBeVisible();
  });
});
