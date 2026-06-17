import catalogJson from "@/content/marketing/catalog.json";

import type { MarketingCatalog, MarketingProduct } from "@/lib/marketing-products";

/** Static SSOT fallback when backend catalog API is unreachable (local dev / Playwright). */
export function loadMarketingCatalogFallback(): MarketingCatalog {
  return catalogJson as MarketingCatalog;
}

export function findMarketingProductFallback(slug: string): MarketingProduct | null {
  const catalog = loadMarketingCatalogFallback();
  return catalog.products.find((row) => row.slug === slug) ?? null;
}
