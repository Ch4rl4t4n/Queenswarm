import { resolveInternalBackendOrigin } from "@/lib/backend-origin";

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
  const res = await fetch(`${origin}/api/v1/marketing/products`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) {
    throw new Error(`Marketing catalog unavailable (${res.status}).`);
  }
  return (await res.json()) as MarketingCatalog;
}

export async function fetchMarketingProduct(slug: string): Promise<MarketingProduct | null> {
  const origin = resolveInternalBackendOrigin();
  const res = await fetch(`${origin}/api/v1/marketing/products/${encodeURIComponent(slug)}`, {
    next: { revalidate: 300 },
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`Marketing product unavailable (${res.status}).`);
  }
  return (await res.json()) as MarketingProduct;
}
