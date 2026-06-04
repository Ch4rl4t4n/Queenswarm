import { defineConfig, devices } from "@playwright/test";

/**
 * Local/dev: spins ``next dev`` on ``PLAYWRIGHT_DEV_PORT`` (default 3000, CI default 4310).
 * Probe a remote hive: ``PLAYWRIGHT_BASE_URL=https://queenswarm.love`` disables the webServer.
 */

const devPort =
  process.env.PLAYWRIGHT_DEV_PORT ?? (process.env.CI ? "4310" : "3000");

const userBaseRaw = process.env.PLAYWRIGHT_BASE_URL?.trim();
const baseURL = (
  userBaseRaw && userBaseRaw.length > 0 ? userBaseRaw : `http://localhost:${devPort}`
).replace(/\/$/, "");

const bypassWebServer =
  !!process.env.PLAYWRIGHT_NO_WEBSERVER ||
  (!!userBaseRaw && userBaseRaw.length > 0);

/** Mirror prod solo operator build flags in the test runner (not only Next dev server). */
if (!bypassWebServer) {
  process.env.NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED ??= "true";
  process.env.NEXT_PUBLIC_SIMULATIONS_ENABLED ??= "true";
  process.env.NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED ??= "true";
  process.env.NEXT_PUBLIC_PHASE70_CONSOLIDATED_NAV_ENABLED ??= "true";
  process.env.NEXT_PUBLIC_RECIPES_ENABLED ??= "true";
  process.env.NEXT_PUBLIC_SOLO_MODE ??= "true";
  process.env.NEXT_PUBLIC_SINGLE_ADMIN_MODE ??= "true";
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"]],
  snapshotPathTemplate: "{testDir}/{testFileDir}/__screenshots__/{testFileName}/{arg}{ext}",
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.025,
      animations: "disabled",
    },
  },
  use: {
    baseURL,
    trace: "retain-on-failure",
    ignoreHTTPSErrors: !!process.env.PLAYWRIGHT_IGNORE_TLS_ERRORS,
  },
  ...(bypassWebServer
    ? {}
    : {
        webServer: {
          command: "npm run dev",
          cwd: ".",
          env: {
            ...process.env,
            PORT: devPort,
            NEXT_PUBLIC_ADVANCED_MONITORING_ENABLED: "true",
            NEXT_PUBLIC_SIMULATIONS_ENABLED: "true",
            NEXT_PUBLIC_OPERATOR_CONTROL_PLANE_ENABLED: "true",
            NEXT_PUBLIC_PHASE70_CONSOLIDATED_NAV_ENABLED: "true",
            NEXT_PUBLIC_RECIPES_ENABLED: "true",
            NEXT_PUBLIC_SOLO_MODE: "true",
            NEXT_PUBLIC_SINGLE_ADMIN_MODE: "true",
          },
          url: `${baseURL}/login`,
          timeout: 240_000,
          reuseExistingServer: !process.env.CI,
          stdout: "pipe",
          stderr: "pipe",
        },
      }),
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
