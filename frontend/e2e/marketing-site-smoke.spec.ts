import { expect, test } from "@playwright/test";

const MARKETING_HEADERS = { "x-e2e-marketing-site": "1" } as const;

const SAMPLE_SLUG = "newsletter-growth-loop-with-verified-outcomes-5";

test.describe("Marketing site smoke (M5)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setExtraHTTPHeaders(MARKETING_HEADERS);
  });

  test("marketing home renders verified skills hero", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Verified agent skills/i })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByRole("link", { name: /Browse the catalog/i })).toBeVisible();
  });

  test("skills catalog lists verified products", async ({ page }) => {
    await page.goto("/skills", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByText("Skill catalog", { exact: true })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Newsletter Growth Loop/i).first()).toBeVisible({ timeout: 30_000 });
  });

  test("product detail page renders scorecard and cover art", async ({ page }) => {
    await page.goto(`/skills/${SAMPLE_SLUG}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Newsletter Growth Loop/i })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/cover\.html preview/i)).toBeVisible();
  });

  test("OG image routes return PNG (cover.html style)", async ({ request }) => {
    for (const path of ["/opengraph-image", "/skills/opengraph-image", `/skills/${SAMPLE_SLUG}/opengraph-image`]) {
      const res = await request.get(path, { headers: MARKETING_HEADERS });
      expect(res.status(), path).toBe(200);
      expect(res.headers()["content-type"] ?? "", path).toContain("image/png");
      const body = await res.body();
      expect(body.byteLength, path).toBeGreaterThan(512);
    }
  });
});
