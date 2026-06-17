import { expect, test } from "@playwright/test";

import { seedDashboardSessionCookie } from "./fixtures/dashboard-session";
import { e2eTasksHubHeading } from "./fixtures/hive-home-route";
import { maybeInstallShellApiMocks } from "./fixtures/shell-api-mocks";
import { suppressPwaInstallPrompt } from "./fixtures/pwa-test-hints";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1280, height: 900 },
] as const;

const STUB_FIRST_RUN_INCOMPLETE = {
  enabled: true,
  complete: false,
  progress_pct: 33,
  steps: [
    {
      id: "llm_keys",
      label: "LLM keys",
      detail: "Add at least one provider.",
      done: false,
      href: "/settings/llm-keys",
      link_label: "Open LLM keys",
    },
    {
      id: "project_brief",
      label: "Project brief",
      detail: "Write a PROJECT block.",
      done: false,
      href: "/knowledge#memory",
      link_label: "Open Curated memory",
    },
    {
      id: "first_session",
      label: "First supervisor session",
      detail: "Create a session with a structured goal.",
      done: false,
      href: "/agents#sessions",
      link_label: "Open session composer",
    },
  ],
  capability: {
    headline: "Your verified agent operating system",
    subhead: "Queenswarm runs supervisor missions with simulate-first verify.",
    bullets: ["One Process Rail", "Mission Kanban", "Brain Pack"],
  },
};

const STUB_MISSION_HOME_SETUP = {
  enabled: true,
  generated_at: new Date().toISOString(),
  current_step: "setup",
  process_steps: [
    { id: "setup", label: "Setup", short_label: "Setup" },
    { id: "plan", label: "Plan", short_label: "Plan" },
    { id: "work", label: "Work", short_label: "Work" },
    { id: "verify", label: "Verify", short_label: "Verify" },
    { id: "learn", label: "Learn", short_label: "Learn" },
    { id: "done", label: "Done", short_label: "Done" },
  ],
  brief_bullets: [{ text: "Run the 3 Bees trio to populate today's brief.", source: "empty_state" }],
  next_actions: [],
  approvals: [],
  active_sessions: [],
  memory_strip: {
    layers: [
      {
        id: "soul",
        label: "SOUL",
        preview: "Empty — load Brain Pack starter in Knowledge.",
        char_count: 0,
        filled: false,
        href: "/knowledge?tab=memory#brain-pack",
      },
    ],
    total_chars: 0,
    max_chars: 80000,
    usage_pct: 0,
  },
  step_studios: [
    {
      id: "llm_keys",
      title: "LLM keys",
      detail: "Configure Grok or OpenRouter.",
      href: "/settings/llm-keys",
    },
  ],
  first_run_complete: false,
  rapid_loop_widget_enabled: true,
  sub_swarm_fleet_widget_enabled: true,
  factory_launch_widget_enabled: true,
  links: {
    new_session: "/agents#sessions",
    approvals: "/cockpit#approvals",
    knowledge: "/knowledge#memory",
    kanban: "/tasks",
  },
};

async function installFirstRunJourneyMocks(page: import("@playwright/test").Page): Promise<void> {
  await page.route("**/api/proxy/solo-operator/first-run**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STUB_FIRST_RUN_INCOMPLETE),
    });
  });
  await page.route("**/api/proxy/solo-operator/mission-home**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(STUB_MISSION_HOME_SETUP),
    });
  });
}

test.describe("First-run journey — Track Q UX9", () => {
  test.beforeEach(async ({ page }) => {
    await maybeInstallShellApiMocks(page);
    await installFirstRunJourneyMocks(page);
    await suppressPwaInstallPrompt(page);
  });

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} · Mission Home shows setup Process Rail`, async ({ page, context, baseURL }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

      await page.goto("/tasks", { waitUntil: "load", timeout: 60_000 });
      await expect(page.getByRole("heading", { name: e2eTasksHubHeading() })).toBeVisible({ timeout: 30_000 });
      await expect(page.locator("#mission-home")).toBeVisible({ timeout: 20_000 });
      await expect(page.getByTestId("rapid-loop-widget")).toBeVisible({ timeout: 20_000 });
      await expect(page.getByRole("navigation", { name: "Operator process" })).toBeVisible();
      await expect(page.getByRole("link", { name: /LLM keys/i })).toBeVisible();
      if (viewport.name !== "desktop") {
        await expect(page.getByRole("link", { name: /Finish first-run setup/i })).toBeVisible();
      }
    });
  }

  test("mobile bottom nav shows four solo primaries", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");
    await page.goto("/tasks", { waitUntil: "load", timeout: 60_000 });

    const nav = page.getByRole("navigation", { name: "Primary mobile navigation" });
    await expect(nav).toBeVisible({ timeout: 20_000 });
    await expect(nav.getByRole("link", { name: /Mission Control/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /^Agents$/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /^Knowledge$/i })).toBeVisible();
    await expect(nav.getByRole("link", { name: /^Integrations$/i })).toBeVisible();
  });

  test("agents first-run wizard shows capability hero and checklist", async ({ page, context, baseURL }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.addInitScript(() => {
      localStorage.removeItem("qs_first_run_wizard_dismissed");
    });
    await seedDashboardSessionCookie(context, baseURL ?? "http://localhost:4310");

    await page.goto("/agents#sessions", { waitUntil: "load", timeout: 60_000 });
    const wizard = page.locator("#first-run-wizard");
    await expect(wizard).toBeVisible({ timeout: 30_000 });
    await expect(wizard.getByText("Your verified agent operating system")).toBeVisible();
    await expect(wizard.getByRole("link", { name: /Open LLM keys/i })).toBeVisible();
  });
});
