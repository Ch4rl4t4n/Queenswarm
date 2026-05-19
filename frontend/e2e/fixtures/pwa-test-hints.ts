import type { Page } from "@playwright/test";

/** Prevent install prompt from obscuring layout / visual snapshots in E2E. */
export async function suppressPwaInstallPrompt(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("qs_pwa_install_dismissed", String(Date.now() + 86_400_000));
  });
}
