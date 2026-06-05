import type { Metadata } from "next";

import { CatalogPageClient } from "@/components/marketing/catalog-page-client";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { toMarketingProductView } from "@/lib/marketing-catalog-view";
import { fetchMarketingCatalog } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Skill catalog · Let Agents Cook",
  description: "Browse verified agent skills and content packs. Buy on external marketplaces.",
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
