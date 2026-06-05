import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { ProductCard } from "@/components/marketing/product-card";
import { hiveOverviewHref } from "@/lib/hive-home-route";
import { isMarketingHost } from "@/lib/marketing-host";
import { fetchMarketingCatalog } from "@/lib/marketing-products";

export const metadata: Metadata = {
  title: "Let Agents Cook — Verified agent skills",
  description:
    "Verified agent skills and content packs — simulate-first, sell with confidence.",
};

export default async function RootPage(): Promise<JSX.Element> {
  const host = (await headers()).get("host");
  if (!isMarketingHost(host)) {
    redirect(hiveOverviewHref());
  }

  const catalog = await fetchMarketingCatalog();
  const featured = catalog.products.filter((product) => product.featured).slice(0, 3);

  return (
    <MarketingShell>
      <section className="mx-auto max-w-6xl px-4 py-16">
        <p className="text-xs uppercase tracking-[0.2em] text-pollen">Let Agents Cook</p>
        <h1 className="mt-3 max-w-3xl font-[family-name:var(--font-hive-display)] text-4xl font-bold leading-tight md:text-5xl">
          Verified agent skills and content packs — simulate-first, sell with confidence.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-(--qs-text-2)">
          Every listing ships with guardrails, harness files, and a quality score. Browse here, buy on external
          marketplaces — professional delivery, not prompt dumps.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/skills" className="qs-btn qs-btn--primary">
            Browse {catalog.product_count} verified listings
          </Link>
          <Link href="/skills" className="qs-btn qs-btn--ghost">
            See featured skills
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="font-[family-name:var(--font-hive-display)] text-2xl font-semibold">Featured listings</h2>
            <p className="mt-1 text-sm text-(--qs-text-3)">Highest-potential verified skills and content packs.</p>
          </div>
          <Link href="/skills" className="text-sm text-data hover:underline">
            View all
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {featured.map((product) => (
            <ProductCard key={product.slug} product={product} />
          ))}
        </div>
      </section>
    </MarketingShell>
  );
}
