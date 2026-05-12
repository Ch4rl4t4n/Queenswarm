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

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"]],
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
          env: { ...process.env, PORT: devPort },
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
