import type { Metadata } from "next";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { ProductCard } from "@/components/marketing/product-card";
import { fetchMarketingCatalog } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Verified skills catalog · Let Agents Cook",
  description: "Browse verified agent skills and content packs. Buy on external marketplaces.",
};

export default async function SkillsCatalogPage(): Promise<JSX.Element> {
  const catalog = await fetchMarketingCatalog();

  return (
    <MarketingShell>
      <section className="mx-auto max-w-6xl px-4 py-12">
        <p className="text-xs uppercase tracking-[0.2em] text-pollen">Catalog</p>
        <h1 className="mt-2 font-[family-name:var(--font-hive-display)] text-3xl font-bold md:text-4xl">
          Verified skills and content packs
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-(--qs-text-2)">
          {catalog.product_count} scorecard-clean listings. Only simulate-first bundles with harness files,
          guardrails, and professional packaging.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {catalog.products.map((product) => (
            <ProductCard key={product.slug} product={product} />
          ))}
        </div>
        <p className="mt-10 text-sm text-(--qs-text-3)">
          Each product page links to external marketplaces (Gumroad and others as listed). No app signup — buy and
          download the bundle from the marketplace.
        </p>
      </section>
    </MarketingShell>
  );
}
