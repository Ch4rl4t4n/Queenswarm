import type { Metadata } from "next";

import { CatalogPageClient } from "@/components/marketing/catalog-page-client";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { marketingPublicOrigin } from "@/lib/marketing-host";
import { toMarketingProductView } from "@/lib/marketing-catalog-view";
import { fetchMarketingCatalog } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Skill catalog · Let Agents Cook",
  description: "Browse verified agent skills and content packs. Buy on external marketplaces.",
  openGraph: {
    title: "Skill catalog · Let Agents Cook",
    description: "Browse verified agent skills and content packs. Buy on external marketplaces.",
    type: "website",
    url: `${marketingPublicOrigin()}/skills`,
    images: [{ url: "/skills/opengraph-image", width: 1200, height: 630, alt: "Let Agents Cook catalog" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Skill catalog · Let Agents Cook",
    description: "Browse verified agent skills and content packs.",
    images: ["/skills/opengraph-image"],
  },
};

export default async function SkillsCatalogPage(): Promise<JSX.Element> {
  const catalog = await fetchMarketingCatalog();
  const products = catalog.products.map(toMarketingProductView);

  return (
    <MarketingShell>
      <CatalogPageClient products={products} />
    </MarketingShell>
  );
}
