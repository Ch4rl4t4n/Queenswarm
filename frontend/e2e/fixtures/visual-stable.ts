import type { Page } from "@playwright/test";

/** Disable motion and wait for fonts before visual snapshots. */
export async function stabilizePageForScreenshot(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
      }
    `,
  });

  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
  });

  await page.waitForTimeout(150);
}
