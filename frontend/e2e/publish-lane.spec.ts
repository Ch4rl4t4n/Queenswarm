import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import {
  clearIntegrationsSubnavPrefs,
  installExecutionStudioApiMocks,
} from "./fixtures/execution-studio-api-mocks";
import { installShellApiMocks } from "./fixtures/shell-api-mocks";

const publishLaneE2eEnabled = process.env.E2E_PUBLISH_LANE === "1";

const PUBLISH_QUEUE_SNAPSHOT = {
  enabled: true,
  count: 1,
  pending_count: 1,
  approved_count: 0,
  rejected_count: 0,
  auto_approve_enabled: false,
  items: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      title: "Launch post",
      channel: "instagram",
      body: "Hello Queenswarm",
      body_preview: "Hello Queenswarm",
      hashtags: ["ai"],
      cta: "Learn more",
      media_url: "https://cdn.example.com/post.jpg",
      media_kind: "image",
      status: "pending",
      created_at: new Date().toISOString(),
      supervisor_session_id: null,
      tags: ["publish-pack-verified"],
    },
  ],
};

const SOCIAL_PUBLISH_SNAPSHOT = {
  enabled: true,
  live_enabled: false,
  generated_at: new Date().toISOString(),
  channels: [
    {
      channel: "instagram",
      label: "Instagram",
      connector_slug: "instagram_graph",
      template_id: "instagram_graph_api",
      installed: true,
      active: true,
      credentials_ok: true,
      publish_tool: "media_create",
      live_allowed: false,
    },
  ],
  ready_items: [],
  audit: {
    enabled: true,
    count: 1,
    entries: [
      {
        at: new Date().toISOString(),
        kind: "social_simulate",
        message: "OK",
        title: "Launch",
        channel: "instagram",
        mode: "simulate",
        ok: true,
      },
    ],
  },
  trusted_auto: {
    global_enabled: false,
    tenant_enabled: false,
    min_simulates_required: 5,
    live_enabled: false,
    channels: [],
  },
  rate_limit: {
    enabled: true,
    fail_closed: true,
    window_hours: 24,
    global_used: 0,
    global_max: 30,
    global_remaining: 30,
    redis_ok: true,
    channels: [],
  },
  links: { publish_queue: "/integrations?tab=studio&section=publish#publish-queue" },
};

async function openExecutionStudioPublish(page: import("@playwright/test").Page): Promise<void> {
  const overviewReady = page.waitForResponse(
    (res) => res.url().includes("/api/proxy/execution-studio/overview") && res.ok(),
    { timeout: 90_000 },
  );
  await page.goto("/integrations?tab=studio&section=publish", {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await expect(page.getByRole("heading", { name: "Integrations", exact: true })).toBeVisible({
    timeout: 45_000,
  });
  await overviewReady;
  await expect(page.getByRole("heading", { name: /Execution Studio/i }).first()).toBeVisible({
    timeout: 45_000,
  });
  await expect(page.getByRole("button", { name: "Publish", exact: true })).toHaveAttribute(
    "aria-current",
    "page",
  );
}

test.describe("Publish lane panels", () => {
  test.setTimeout(120_000);

  test.beforeEach(async ({ context, baseURL, page }) => {
    test.skip(!publishLaneE2eEnabled, "Set E2E_PUBLISH_LANE=1 to run publish lane smoke.");

    await clearIntegrationsSubnavPrefs(page);
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await installShellApiMocks(page);
    await installExecutionStudioApiMocks(page);

    await page.route("**/api/proxy/publish-queue", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(PUBLISH_QUEUE_SNAPSHOT),
      });
    });
    await page.route("**/api/proxy/social-publish", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(SOCIAL_PUBLISH_SNAPSHOT),
      });
    });
    await page.route("https://cdn.example.com/post.jpg", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: Buffer.from(
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
          "base64",
        ),
      });
    });
  });

  test("Execution Studio shows publish queue media preview and social publish rate limits", async ({
    page,
  }) => {
    await openExecutionStudioPublish(page);
    const publishQueue = page.locator("#publish-queue");
    await expect(publishQueue).toBeVisible({ timeout: 45_000 });
    await expect(publishQueue.getByText("Launch post")).toBeVisible();
    await publishQueue.getByRole("button", { name: /^Details$/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog").locator("img[alt='Launch post']")).toBeVisible();
    await expect(page.locator("#social-publish")).toBeVisible();
    await expect(page.locator("#social-publish").getByText(/Live rate limits/i)).toBeVisible();
  });
});
