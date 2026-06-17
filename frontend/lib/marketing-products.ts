import { resolveInternalBackendOrigin } from "@/lib/backend-origin";
import {
  findMarketingProductFallback,
  loadMarketingCatalogFallback,
} from "@/lib/marketing-catalog-fallback";

export interface MarketingProduct {
  slug: string;
  kind: string;
  title: string;
  subtitle: string;
  price: string;
  score: number;
  scorecard_verdict?: string;
  scorecard_clean?: boolean;
  featured: boolean;
  gumroad_url: string | null;
  package_dir: string | null;
}

export interface MarketingCatalog {
  generated_from: string;
  product_count: number;
  featured_slugs: string[];
  products: MarketingProduct[];
}

export async function fetchMarketingCatalog(): Promise<MarketingCatalog> {
  const origin = resolveInternalBackendOrigin();
  try {
    const res = await fetch(`${origin}/api/v1/marketing/products`, {
      next: { revalidate: 300 },
    });
    if (res.ok) {
      return (await res.json()) as MarketingCatalog;
    }
  } catch {
    /* fall back to bundled catalog for marketing smoke / offline dev */
  }
  return loadMarketingCatalogFallback();
}

export async function fetchMarketingProduct(slug: string): Promise<MarketingProduct | null> {
  const origin = resolveInternalBackendOrigin();
  try {
    const res = await fetch(`${origin}/api/v1/marketing/products/${encodeURIComponent(slug)}`, {
      next: { revalidate: 300 },
    });
    if (res.status === 404) {
      return findMarketingProductFallback(slug);
    }
    if (res.ok) {
      return (await res.json()) as MarketingProduct;
    }
  } catch {
    /* fall back to bundled catalog for marketing smoke / offline dev */
  }
  return findMarketingProductFallback(slug);
}
