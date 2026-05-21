import { expect, test } from "@playwright/test";

const enabled = process.env.E2E_PROD_PUBLIC === "1";

const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 900 },
] as const;

const MAGNETS = ["exec-assistant", "lead-waterfall", "content-flywheel"] as const;

async function assertNoHorizontalOverflow(page: import("@playwright/test").Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > root.clientWidth + 1;
  });
  expect(overflow, "page should not scroll horizontally").toBe(false);
}

test.describe("Prod public walkthrough", () => {
  test.skip(!enabled, "Set E2E_PROD_PUBLIC=1 to run prod public walkthrough.");

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} login has no horizontal overflow`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/login", { waitUntil: "load", timeout: 60_000 });
      await expect(page.getByRole("button", { name: /continue/i })).toBeVisible({ timeout: 30_000 });
      await assertNoHorizontalOverflow(page);
    });
  }

  for (const magnet of MAGNETS) {
    test(`magnet landing /magnet/${magnet} loads`, async ({ page }) => {
      await page.goto(`/magnet/${magnet}`, { waitUntil: "load", timeout: 60_000 });
      await expect(page.locator("main, body").first()).toBeVisible({ timeout: 30_000 });
      expect(page.url()).toContain(`/magnet/${magnet}`);
    });
  }
});
